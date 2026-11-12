# *********************************************************************
# This Original Work is copyright of 51 Degrees Mobile Experts Limited.
# Copyright 2026 51 Degrees Mobile Experts Limited, Davidson House,
# Forbury Square, Reading, Berkshire, United Kingdom RG1 3EU.
#
# This Original Work is licensed under the European Union Public Licence
# (EUPL) v.1.2 and is subject to its terms as set out below.
#
# If a copy of the EUPL was not distributed with this file, You can obtain
# one at https://opensource.org/licenses/EUPL-1.2.
#
# The 'Compatible Licences' set out in the Appendix to the EUPL (as may be
# amended by the European Commission) shall be deemed incompatible for
# the purposes of the Work and the provisions of the compatibility
# clause in Article 5 of the EUPL shall not apply.
#
# If using the Work as, or as part of, a network application, by
# including the attribution notice(s) required under Article 5 of the EUPL
# in the end user terms of the application under an appropriate heading,
# such notice(s) shall fulfill the requirements of that article.
# *********************************************************************

import calendar
import datetime
from email.utils import formatdate
from enum import Enum
import gzip
import shutil
import os
import random
import threading
import time
import zlib
import requests
from fiftyone_pipeline_core.keymask import mask_licence_keys_in_text


class UpdateStatus(Enum):
    # Update completed successfully.
    AUTO_UPDATE_SUCCESS = 0
    # HTTPS connection could not be established.
    AUTO_UPDATE_HTTPS_ERR = 1
    # No need to perform update.
    AUTO_UPDATE_NOT_NEEDED = 2
    # Update currently under way.
    AUTO_UPDATE_IN_PROGRESS = 3
    # Path to master file is directory not file
    AUTO_UPDATE_MASTER_FILE_CANT_RENAME = 4
    # 51Degrees server responded with 429: too many attempts.
    AUTO_UPDATE_ERR_429_TOO_MANY_ATTEMPTS = 5
    # 51Degrees server responded with 403 meaning key is blacklisted.
    AUTO_UPDATE_ERR_403_FORBIDDEN = 6
    # Used when IO operations with input or output stream failed.
    AUTO_UPDATE_ERR_READING_STREAM = 7
    # MD5 validation failed
    AUTO_UPDATE_ERR_MD5_VALIDATION_FAILED = 8
    # The new data file can't be renamed to replace the previous one.
    AUTO_UPDATE_NEW_FILE_CANT_RENAME = 9
    # Refreshing the engine with the new data caused an error to occur.
    AUTO_UPDATE_REFRESH_FAILED = 10
    # 11 is .NET's AUTO_UPDATE_NO_CONFIGURATION, which this service has no
    # route to, so the two below keep the numbers .NET gives them.
    # The data file is checking for updates but has no temporary file path.
    AUTO_UPDATE_TEMP_PATH_NOT_SET = 12
    # Any other error during a check for an update.
    AUTO_UPDATE_UNKNOWN_ERROR = 13

# The first two bytes of gzip compressed content (RFC 1952 section 2.3.1).
GZIP_MAGIC = b"\x1f\x8b"

# The tries made to refresh an engine from a data file, which the message
# for a failed refresh names.
REFRESH_TRIES = 1


class DataFileUpdateService():

    """!
    A data file update service is attached to a pipeline and manages
    the download of datafiles used by engines
    """

    # Time between the file system watcher's checks of a data file.
    FILE_SYSTEM_WATCHER_INTERVAL_SECONDS = 10

    def __init__(self, pipeline = None):
     
        """!
        Constructor for the DataFileUpdateService
        @type pipeline: Pipeline
        @param pipeline: The pipeline the datafile update service is attached to
        """
        if pipeline != None:
            self.pipeline = pipeline
        self.on_complete_methods = []

    def __emit(self, status, data_file):
        # A callback that raises stops the callbacks after it, as .NET's service
        # does, and its error is logged with .NET's message for any other
        # error, so that the next check still runs.
        try:
            for method in self.on_complete_methods:
                method(status, data_file)
        except Exception as e:
            self._log_unhandled(data_file, e)

    def update_data_file(self, data_file):

        """!
        Function to request, download, check and unzip a datafile from
        an update service via an HTTP request
        @type data_file: DataFile
        @param data_file: Datafile to update
        """

        # A data file whose engine has been closed is not updated.
        if not self.__is_registered(data_file):
            return False

        # exit if already updating

        if data_file.updating:
            pass

        self._log("info", "Checking for update")

        # Get the update url

        url = data_file.get_update_url()
        # The URL carries the licence key, so only a masked copy is logged.
        shown_url = mask_licence_keys_in_text(url)
        engine = self._engine_type(data_file)

        headers = {}

        status = UpdateStatus.AUTO_UPDATE_IN_PROGRESS

        # Add if modified since header if enabled and available
        since = None
        if data_file.verify_if_modified_since:
            since = self._if_modified_since(data_file)
            if since:
                headers["If-Modified-Since"] = since

        self._log(
            "info",
            "Checking for update from '" + shown_url + "' for Engine '" +
            engine + "'")

        try:
            response = requests.get(url, headers=headers)
        except requests.RequestException as e:
            # The message of a failed request names the URL, key included.
            self._log_check_error(
                "Error accessing data update service at '" + shown_url +
                "' for engine '" + engine + "'",
                mask_licence_keys_in_text(e))
            return self._update_failed(
                data_file, UpdateStatus.AUTO_UPDATE_HTTPS_ERR)

        if response is None:
            self._log_check_error(
                "No response from data update service at '" + shown_url +
                "' for engine '" + engine + "'")
            return self._update_failed(
                data_file, UpdateStatus.AUTO_UPDATE_HTTPS_ERR)

        if response.status_code == 304:
            self._log(
                "info",
                "No data newer than " + (since or "the data in use") +
                " found at '" + shown_url + "' for Engine '" + engine +
                "'")
            return self._update_failed(
                data_file, UpdateStatus.AUTO_UPDATE_NOT_NEEDED)

        if response.status_code != 200:

            # Each response that is not a success and not a 304 carries the
            # message and status of the matching row of the errors table.

            if response.status_code == 429:
                status = UpdateStatus.AUTO_UPDATE_ERR_429_TOO_MANY_ATTEMPTS
                message = ("Too many requests to '" + shown_url +
                           "' for engine '" + engine + "'")
            elif response.status_code == 403:
                status = UpdateStatus.AUTO_UPDATE_ERR_403_FORBIDDEN
                message = ("Access denied to data update service at '" +
                           shown_url + "' for engine '" + engine + "'")
            else:
                status = UpdateStatus.AUTO_UPDATE_HTTPS_ERR
                message = ("HTTP status code '" +
                           str(response.status_code) +
                           "' from data update service at '" + shown_url +
                           "' for engine '" + engine + "'")

            self._log_check_error(message)
            return self._update_failed(data_file, status)

        # Verify the MD5 hash if enabled and the answer gives one.

        header_md5 = response.headers.get("content-md5")
        if data_file.verify_md5 and header_md5 is None:
            self._log(
                "warning",
                "No MD5 hash included in data update response for '" +
                shown_url + "'. Unable to verify data integrity")
        elif data_file.verify_md5:

            import hashlib
            hash_md5 = hashlib.md5()

            for data in response.iter_content(8192):
                hash_md5.update(data)

            if header_md5 != hash_md5.hexdigest():
                self._log_check_error(
                    "Integrity check failed. MD5 hash in HTTP response '" +
                    str(header_md5) + "' for '" + engine + "'data update "
                    "does not match calculated hash for the downloaded "
                    "file '" + hash_md5.hexdigest() + "'.")
                return self._update_failed(
                    data_file,
                    UpdateStatus.AUTO_UPDATE_ERR_MD5_VALIDATION_FAILED)

        self._log(
            "info",
            "Downloaded new data from '" + shown_url + "' for Engine '" +
            engine + "'")

        data = response.content

        # Decompress if set and the content is compressed.
        if data_file.decompress and data[:2] == GZIP_MAGIC:
            try:
                data = gzip.decompress(data)
            except (OSError, EOFError, zlib.error) as e:
                # Content that cannot be read is any other error, which
                # carries the last row of the errors table.
                self._log_unhandled(data_file, e)
                return self._update_failed(
                    data_file, UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR)

        # Download datafile if needed, or pass through memory
        if data_file.download:
            # The engine of a data file kept on disk reads that file, so a
            # write that failed leaves it with the data it already had and
            # the update ends there, as it does in .NET and
            # 51degrees-node.
            failed = self._write_data_file(data_file, data)
            if failed is not None:
                return self._update_failed(data_file, failed)

        else:

            data_file.data = data

        # If updating on start, cancel as done

        if data_file.update_on_start:
            data_file.updated_on_start = True

        # Done. Refresh the file.

        status = self._refresh(data_file)

        data_file.updating = False

        self.__emit(status, data_file)
        self.check_next_update(data_file)

        return True

    def update_from_memory(self, data_file, data):

        """!
        Refresh a data file from the bytes given, without downloading
        anything. A data file kept on disk has the bytes written to its path
        first, as the update route writes a download, and the engine is then
        refreshed from the file.
        @type data_file: DataFile
        @param data_file: Datafile to update
        @type data: bytes
        @param data: The new content of the data file
        @rtype: UpdateStatus
        @return: AUTO_UPDATE_SUCCESS, AUTO_UPDATE_REFRESH_FAILED if the
        engine could not use the data (the data it had is kept), the status
        of a failed write for a data file kept on disk, which is not
        refreshed because its engine reads the file, or
        AUTO_UPDATE_NOT_NEEDED if the data file's engine has been closed
        """

        if not self.__is_registered(data_file):
            return UpdateStatus.AUTO_UPDATE_NOT_NEEDED

        if data_file.download and getattr(data_file, "path", None):
            data_file.updating = True
            try:
                status = self._write_data_file(data_file, data)
                if status is None:
                    status = self._refresh(data_file)
            finally:
                data_file.updating = False
            self.__emit(status, data_file)
            return status

        previous = data_file.data
        data_file.data = data
        data_file.updating = True
        try:
            status = self._refresh(data_file, from_file=False)
        finally:
            data_file.updating = False

        if status != UpdateStatus.AUTO_UPDATE_SUCCESS:
            data_file.data = previous

        self.__emit(status, data_file)

        return status

    def _write_data_file(self, data_file, data):
        # Write new data to the data file's path, through a temporary copy
        # when the data file asks for one. None when written, or the status
        # of the failure, which is logged. Every failure leaves the file on
        # disk as it was, so the caller ends the update.
        if data_file.create_temp_copy:
            if not getattr(data_file, "temp_directory", None):
                self._log_check_error(
                    "The data file '" + str(data_file.identifier) +
                    "' is checking for updates but does not have a "
                    "temporary file path configured.")
                return UpdateStatus.AUTO_UPDATE_TEMP_PATH_NOT_SET
            filename = os.path.join(
                data_file.temp_directory,
                data_file.identifier + str(time.time()))
        else:
            filename = data_file.path

        try:
            with open(filename, 'wb') as f:
                f.write(data)
        except OSError as e:
            if filename == data_file.path:
                # Writing straight to the data file is the copy that
                # replaces it, so it carries that row of the errors table.
                self._log_check_error(
                    "An error occurred when copying a data file to replace "
                    "the existing one at '" + str(data_file.path) + "'.", e)
            else:
                # A temporary copy that cannot be written has no row of its
                # own, so it is any other error, as 51degrees-node writes
                # it.
                self._log_unhandled(data_file, e)
            return UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME

        if data_file.create_temp_copy:
            try:
                shutil.move(filename, data_file.path)
            except (OSError, shutil.Error) as e:
                self._log_check_error(
                    "An error occurred when copying a data file to "
                    "replace the existing one at '" + data_file.path +
                    "'.", e)
                return UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME
        return None

    def _refresh(self, data_file, from_file=True):
        # Refresh the engine with the data file's new content. A refresh
        # after a check or a watched change is from the data file, and one
        # from update_from_memory is not, as the two rows of the errors
        # table say.
        engine = self._engine_type(data_file)
        self._log(
            "info",
            "Attempting to refresh Engine '" + engine + "' with new data")
        try:
            data_file.refresh()
        except Exception as e:
            self._log_check_error(
                "An error occurred when applying a data update to engine '" +
                engine + "'" +
                (" after " + str(REFRESH_TRIES) + " tries." if from_file
                 else "."), e)
            return UpdateStatus.AUTO_UPDATE_REFRESH_FAILED
        return UpdateStatus.AUTO_UPDATE_SUCCESS

    def _update_failed(self, data_file, status):
        # An update that ends without new data. The next check is the next
        # scheduled one, never an immediate repeat of a check on start-up.
        data_file.updating = False
        self.__emit(status, data_file)
        self.check_next_update(data_file, run_after_error=True)
        return False

    def _log(self, level, message):
        pipeline = getattr(self, "pipeline", None)
        if pipeline is not None:
            pipeline.log(level, message)

    def _log_check_error(self, text, cause=None):
        # An error from a row of the errors table at Error level is logged
        # as .NET logs a DataUpdateException, under .NET's entry text with
        # the error, being the row's text and then its cause, after it, in
        # the words 51degrees-node writes.
        self._log(
            "error",
            self._with_cause(
                self._with_cause("Error during check for data update", text),
                cause))

    def _log_unhandled(self, data_file, cause):
        # Any other error is logged with the last row's message, and the
        # error after it.
        self._log(
            "error",
            self._with_cause(
                "An unhandled error occurred while checking for automatic "
                "updates for engine '" + self._engine_type(data_file) + "'",
                cause))

    @staticmethod
    def _with_cause(text, cause):
        if cause is None:
            return text
        return (text + ("" if text.endswith(".") else ".") +
                " Error detail: " + str(cause))

    @staticmethod
    def _engine_type(data_file):
        return type(getattr(data_file, "flow_element", data_file)).__name__

    @staticmethod
    def _http_date(moment):
        # An HTTP date, as RFC 9110 section 5.6.7 requires. A time with no
        # zone is taken as UTC.
        if isinstance(moment, datetime.datetime):
            fields = moment.utctimetuple()
        else:
            fields = moment.timetuple()
        return formatdate(calendar.timegm(fields), usegmt=True)

    def _if_modified_since(self, data_file):
        # The publication date of the data file, or the time the file was
        # last modified when it has no publication date. None when neither
        # is known.
        try:
            published = data_file.get_date_published()
        except Exception:
            published = None
        if published is None:
            path = getattr(data_file, "path", None)
            try:
                published = datetime.datetime.fromtimestamp(
                    os.path.getmtime(path), datetime.timezone.utc)
            except (OSError, TypeError):
                return None
        return self._http_date(published)

    @staticmethod
    def _seconds_until_update_expected(data_file):
        # Seconds from now until the data file says new data is expected, or
        # 0 when it does not say or the time has passed. A date with no time
        # is the default of a data file that does not know.
        try:
            expected = data_file.get_next_update()
        except Exception:
            return 0
        utc = datetime.timezone.utc
        if isinstance(expected, datetime.datetime):
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=utc)
        elif isinstance(expected, datetime.date):
            if expected <= datetime.date.today():
                return 0
            expected = datetime.datetime(
                expected.year, expected.month, expected.day, tzinfo=utc)
        else:
            return 0
        return max(0, (expected - datetime.datetime.now(utc)).total_seconds())

    def async_update_data_file(self, data_file):

        """!
        Non blocking version of update_data_file
        @type data_file: DataFile
        @param data_file: Datafile to update
        """
        
        thread = threading.Thread(name="Update service", target=self.update_data_file, args=[data_file], daemon=True)
        thread.start()
        return thread
    
    def check_next_update(self, data_file, run_after_error = False):
        """!
        Function to periodically check if a datafile needs updating
        also updates the datafile on start if it is set with the update_on_start option.
        Polling does not start until after the time the data file expects
        new data, if it gives one.
        @type data_file: DataFile
        @param data_file: Datafile to check updates for
        """

        if not self.__is_registered(data_file):
            return

        if data_file.update_on_start and not data_file.updated_on_start and not run_after_error:
            self._log("info", "Updating on start-up")
            self.update_data_file(data_file)

        elif data_file.auto_update:

            random_offset = random.randint(0, data_file.update_time_maximum_randomisation)

            interval = random_offset + (data_file.polling_interval * 60)
            until_expected = self._seconds_until_update_expected(data_file)
            if until_expected > 0:
                interval = until_expected + random_offset
            t = threading.Timer(interval, self.async_update_data_file, args=[data_file])
            t.daemon = True
            t.name = "AutoUpdate - Scheduled"
            data_file.update_timer = t
            t.start()

    def register_pipeline(self, pipeline):
        self.pipeline = pipeline

    def register_data_file(self, data_file):
        """!
        Function to register a datafile with the update service
        @type data_file: DataFile
        @param data_file: Datafile to check updates for
        """

        data_file.registered = True

        if data_file.update_on_start or data_file.auto_update:
            self.check_next_update(data_file)

        # Watch for changes in file and refresh if
        # file_system_watcher is enabled on data_file

        # The watcher is an automatic update, so it only runs with
        # automatic updates on.
        if data_file.auto_update and data_file.file_system_watcher:
            self._log("info", "Creating file system watcher")
            data_file.last_changed_time = os.stat(data_file.path).st_mtime
            self.track_local_data_file_changes(data_file)    

    def unregister_data_file(self, data_file):
        """!
        Stop the checks and updates of a datafile, for example when its
        engine is closed. Checks already scheduled are cancelled, and a
        check already running schedules no other, so nothing is left
        holding the data file or its engine.
        @type data_file: DataFile
        @param data_file: Datafile to stop checking
        """

        data_file.registered = False
        for name in ("update_timer", "watcher_timer"):
            timer = getattr(data_file, name, None)
            if timer is not None:
                timer.cancel()

    def __is_registered(self, data_file):
        # A data file checked without being registered first is checked as
        # before. Only one that has been unregistered is left alone.
        return getattr(data_file, "registered", True)

    def track_local_data_file_changes(self, data_file):
        """!
        Check for local changes to a datafile. Used by
        the file system watcher. A file that has been written to is an
        event, and the refresh takes the same route as the polling one, so
        the attempt is logged, a failure carries the errors table's message
        and level, and the result is reported to the update complete
        callbacks either way. The next check is scheduled whatever happens,
        so that a later file is still picked up, until the data file is
        unregistered.
        @type data_file: DataFile
        @param data_file: Datafile to check updates for
        """
        if not self.__is_registered(data_file):
            return
        try:
            changed_time = os.stat(data_file.path).st_mtime
        except OSError:
            # A file that is missing, for example part way through being
            # replaced, is looked for again at the next check.
            changed_time = None
        try:
            if (changed_time is None or
                    changed_time <= data_file.last_changed_time):
                # A file nobody has written to is not an event, so nothing
                # is reported. The watchers of .NET and 51degrees-node are
                # told by the operating system and say nothing whilst a
                # file is untouched, and this check stands in for that.
                return
            if data_file.updating:
                # A newer file found whilst an update is being applied is
                # reported as in progress, and the time is not taken, so
                # the next check looks at the file again.
                self.__emit(UpdateStatus.AUTO_UPDATE_IN_PROGRESS, data_file)
                return
            data_file.last_changed_time = changed_time
            self.__emit(self._refresh(data_file), data_file)
        finally:
            if self.__is_registered(data_file):
                t = threading.Timer(
                    self.FILE_SYSTEM_WATCHER_INTERVAL_SECONDS,
                    self.track_local_data_file_changes,
                    args=[data_file])
                t.daemon = True
                t.name = "AutoUpdate - FileWatcher"
                data_file.watcher_timer = t
                t.start()

    def on_complete(self, on_complete_method):
        self.on_complete_methods.append(on_complete_method)

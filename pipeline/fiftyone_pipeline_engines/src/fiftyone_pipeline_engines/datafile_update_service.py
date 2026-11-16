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
import warnings
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
    # A watched file could not be opened for reading in the time allowed.
    AUTO_UPDATE_TIMEOUT = 14


class DataUpdateException(Exception):
    """!
    A data update that failed, which a programmatic check and an update from
    memory raise to their caller. The message is the one the errors table of
    the data updates specification gives for the failure, and the error that
    caused it, if any, is chained as its cause.
    """

    def __init__(self, message, status):
        """!
        @type message: str
        @param message: What failed, naming the engine or the path
        @type status: UpdateStatus
        @param status: The status of the failure
        """
        super(DataUpdateException, self).__init__(message)
        self.status = status


# The first two bytes of gzip compressed content (RFC 1952 section 2.3.1).
GZIP_MAGIC = b"\x1f\x8b"

# REFRESH_TRIES is a module level name of this module that is now
# DataFileUpdateService.REFRESH_TRIES. The old name still reads, with a
# DeprecationWarning, and keeps the value this module gave it, which is
# not the tries the service makes. Nothing in the package reads it.
_DEPRECATED_REFRESH_TRIES = 1

_REFRESH_TRIES_DEPRECATED = (
    "fiftyone_pipeline_engines.datafile_update_service.REFRESH_TRIES is "
    "deprecated and will be removed. It keeps the value 1 it was given "
    "here and is not the tries the service makes, which are "
    "DataFileUpdateService.REFRESH_TRIES.")


def __getattr__(name):
    """!
    Gives the deprecated module level REFRESH_TRIES, with a warning. Any
    other name this module does not hold is missing as usual.
    @type name: str
    @param name: The name read from this module
    @rtype: int
    @return: The value REFRESH_TRIES was given here
    @raise AttributeError: The module holds no name of that name
    """
    if name != "REFRESH_TRIES":
        raise AttributeError(
            "module {0!r} has no attribute {1!r}".format(__name__, name))
    # The second frame is the code that read the name, past this function.
    warnings.warn(_REFRESH_TRIES_DEPRECATED, DeprecationWarning,
                  stacklevel=2)
    return _DEPRECATED_REFRESH_TRIES


class DataFileUpdateService():

    """!
    A data file update service is attached to a pipeline and manages
    the download of datafiles used by engines
    """

    # Time between the file system watcher's checks of a data file.
    FILE_SYSTEM_WATCHER_INTERVAL_SECONDS = 10

    # The tries made to refresh an engine from a data file, and the pause
    # after each that fails, as .NET's data update service makes them. The
    # message for a failed refresh names the tries.
    REFRESH_TRIES = 10
    REFRESH_RETRY_PAUSE_SECONDS = 0.2

    # How long a changed watched file is waited for until it can be opened
    # for reading, as when it is still being copied, and the pause between
    # tries, as .NET waits.
    WATCHED_FILE_WAIT_SECONDS = 600
    WATCHED_FILE_RETRY_PAUSE_SECONDS = 0.5

    def __init__(self, pipeline = None):
     
        """!
        Constructor for the DataFileUpdateService
        @type pipeline: Pipeline
        @param pipeline: The pipeline the datafile update service is attached to
        """
        if pipeline != None:
            self.pipeline = pipeline
        self.on_complete_methods = []
        # Held while a data file's update lock is made and while its pending
        # check is replaced, so two threads cannot make two locks or leave
        # two checks pending.
        self._lock = threading.Lock()
        # The update lock of each data file, by the data file's id.
        self._update_locks = {}

    def _update_lock(self, data_file):
        # One update or file system watcher refresh of a data file runs at a
        # time. A second update waits for the first and then makes its own
        # check, so every check ends and is reported. Re-entrant, so that an
        # update complete callback can start an update of the same data file.
        with self._lock:
            return self._update_locks.setdefault(
                id(data_file), threading.RLock())

    def __emit(self, status, data_file, to_caller=False):
        # A callback that raises stops the callbacks after it, as .NET's
        # service does. On a check run for a caller its error passes to that
        # caller. Otherwise it is logged with .NET's message for any other
        # error and the error itself after it, so that the next check still
        # runs. The error is a caller's, so it is masked as any other text
        # that may name the update URL is.
        try:
            for method in self.on_complete_methods:
                method(status, data_file)
        except Exception as e:
            if to_caller:
                raise
            self._log_unhandled(data_file, e)

    def update_data_file(self, data_file):

        """!
        Check for new data now, download it and refresh the engine with it.
        How the check ended is reported to the update complete callbacks,
        and a failure is then raised to the caller rather than logged.
        @type data_file: DataFile
        @param data_file: Datafile to update
        @rtype: bool
        @return: True when the engine was refreshed with new data, or False
        when there was no new data or the data file's engine has been closed
        @raises DataUpdateException: When the check or the refresh failed,
        with the status and message of that failure, and the engine keeps
        the data it had. The error that caused the failure, if any, is
        chained as its cause. Any other error is reported as
        AUTO_UPDATE_UNKNOWN_ERROR and raised as it is. An error raised by an
        update complete callback is raised as it is, and the callbacks after
        it are not called.
        """

        return self._check(data_file, to_caller=True)

    def _check(self, data_file, to_caller):
        # One check of a data file. How it ended is reported to the update
        # complete callbacks and the next check is scheduled. For a caller,
        # a failure is then raised and not logged. Without one, as for
        # update polling and the update on start-up, a failure from a row of
        # the errors table is logged first, and any other error is raised
        # unreported, for update polling to log and report.

        # A data file whose engine has been closed is not updated.
        if not self.__is_registered(data_file):
            return False

        # The file system watcher reads updating to leave a changed file
        # alone while an update runs.
        with self._update_lock(data_file):
            was_updating = data_file.updating
            data_file.updating = True
            try:
                return self._check_and_report(data_file, to_caller)
            finally:
                data_file.updating = was_updating

    def _check_and_report(self, data_file, to_caller):
        try:
            status = self._update_data_file(data_file)
        except DataUpdateException as e:
            if not to_caller:
                self._log_failed_check(data_file, e)
            self._end_check(data_file, e.status, to_caller)
            if to_caller:
                raise
            return False
        except Exception:
            if to_caller:
                self._end_check(
                    data_file, UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR, True)
            raise
        self._end_check(data_file, status, to_caller)
        return status == UpdateStatus.AUTO_UPDATE_SUCCESS

    def _end_check(self, data_file, status, to_caller=False):
        # Report how a check ended, then schedule the next check even when a
        # callback raised, so that a failure never stops later checks. A
        # check that applied no new data is followed by the next scheduled
        # check, never by an immediate repeat of a check on start-up.
        try:
            self.__emit(status, data_file, to_caller)
        finally:
            self.check_next_update(
                data_file,
                run_after_error=status != UpdateStatus.AUTO_UPDATE_SUCCESS)

    def _update_data_file(self, data_file):
        # Download new data and refresh the engine with it, returning
        # AUTO_UPDATE_SUCCESS, or AUTO_UPDATE_NOT_NEEDED when there was no
        # new data. A failure raises a DataUpdateException with the message
        # and status of its row of the errors table. Nothing is reported, as
        # _check_and_report reports how the check ended.

        self._log("info", "Checking for update")

        # Get the update url

        url = data_file.get_update_url()
        # The URL carries the licence key, so only a masked copy is logged.
        shown_url = mask_licence_keys_in_text(url)
        engine = self._engine_type(data_file)

        headers = {}

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
            failure = None
        except requests.RequestException as e:
            # The message of a failed request names the URL, key included,
            # so its cause is a copy with the key masked. It is raised after
            # this block, so the request's own error is not chained to it.
            failure = self._masked_error(e)
        if failure is not None:
            raise DataUpdateException(
                "Error accessing data update service at '" + shown_url +
                "' for engine '" + engine + "'",
                UpdateStatus.AUTO_UPDATE_HTTPS_ERR) from failure

        if response is None:
            raise DataUpdateException(
                "No response from data update service at '" + shown_url +
                "' for engine '" + engine + "'",
                UpdateStatus.AUTO_UPDATE_HTTPS_ERR)

        if response.status_code == 304:
            self._log(
                "info",
                "No data newer than " + (since or "the data in use") +
                " found at '" + shown_url + "' for Engine '" + engine +
                "'")
            return UpdateStatus.AUTO_UPDATE_NOT_NEEDED

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

            raise DataUpdateException(message, status)

        # A response that ended before the whole file arrived is an error
        # accessing the service. urllib3 2 raises one, which the request
        # above catches, but urllib3 1 gives the bytes that arrived, so the
        # length is checked here as well.
        short = self._cut_short(response)
        if short is not None:
            raise DataUpdateException(
                "Error accessing data update service at '" + shown_url +
                "' for engine '" + engine + "'",
                UpdateStatus.AUTO_UPDATE_HTTPS_ERR) from EOFError(
                "The response ended after " + str(short[0]) + " of the " +
                str(short[1]) + " bytes it gave as its Content-Length.")

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
                raise DataUpdateException(
                    "Integrity check failed. MD5 hash in HTTP response '" +
                    str(header_md5) + "' for '" + engine + "'data update "
                    "does not match calculated hash for the downloaded "
                    "file '" + hash_md5.hexdigest() + "'.",
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
                raise DataUpdateException(
                    self._unhandled_message(data_file),
                    UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR) from e

        # Download datafile if needed, or pass through memory
        if data_file.download:
            # The engine of a data file kept on disk reads that file, so a
            # write that failed leaves it with the data it already had and
            # the update ends there, as it does in .NET and
            # 51degrees-node.
            self._write_data_file(data_file, data)

        else:

            data_file.data = data

        # If updating on start, cancel as done

        if data_file.update_on_start:
            data_file.updated_on_start = True

        # Done. Refresh the file.

        self._refresh(data_file)
        return UpdateStatus.AUTO_UPDATE_SUCCESS

    def update_from_memory(self, data_file, data):

        """!
        Refresh a data file from the bytes given, without downloading
        anything. A data file kept on disk has the bytes written to its path
        first, as the update route writes a download, and the engine is then
        refreshed from the file. When the bytes cannot be written, a warning
        is logged and the engine is refreshed from the bytes, so the file on
        disk keeps the old data. The result goes to the caller alone, so
        nothing is reported to the update complete callbacks, and a failure
        is raised rather than logged.
        @type data_file: DataFile
        @param data_file: Datafile to update
        @type data: bytes
        @param data: The new content of the data file
        @rtype: UpdateStatus
        @return: AUTO_UPDATE_SUCCESS when the engine was refreshed, or
        AUTO_UPDATE_NOT_NEEDED, with nothing done, when the data file's
        engine has been closed
        @raises DataUpdateException: When the engine could not use the
        data, with the status AUTO_UPDATE_REFRESH_FAILED, and the engine
        keeps the data it had. The error that caused the failure is chained
        as its cause.
        """

        if not self.__is_registered(data_file):
            return UpdateStatus.AUTO_UPDATE_NOT_NEEDED

        # Waits for an update of the same data file that is running, as a
        # second update does.
        with self._update_lock(data_file):
            return self._update_from_memory(data_file, data)

    def _update_from_memory(self, data_file, data):
        was_updating = data_file.updating
        if data_file.download and getattr(data_file, "path", None):
            data_file.updating = True
            try:
                try:
                    self._write_data_file(data_file, data)
                except DataUpdateException as e:
                    self._log_write_from_memory_failed(data_file, e)
                    self._refresh_from_bytes(data_file, data)
                else:
                    self._refresh_from_memory(data_file)
            finally:
                data_file.updating = was_updating
            return UpdateStatus.AUTO_UPDATE_SUCCESS

        previous = data_file.data
        data_file.data = data
        data_file.updating = True
        try:
            self._refresh_from_memory(data_file)
        except DataUpdateException:
            # The engine keeps the data it had, so the data file does too.
            data_file.data = previous
            raise
        finally:
            data_file.updating = was_updating

        return UpdateStatus.AUTO_UPDATE_SUCCESS

    def _write_data_file(self, data_file, data):
        # Write new data to the data file's path, through a temporary copy
        # when the data file asks for one. A failure raises a
        # DataUpdateException with the message and status of its row of the
        # errors table, and leaves the file on disk as it was.
        if data_file.create_temp_copy:
            if not getattr(data_file, "temp_directory", None):
                raise DataUpdateException(
                    "The data file '" + str(data_file.identifier) +
                    "' is checking for updates but does not have a "
                    "temporary file path configured.",
                    UpdateStatus.AUTO_UPDATE_TEMP_PATH_NOT_SET)
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
                raise DataUpdateException(
                    "An error occurred when copying a data file to replace "
                    "the existing one at '" + str(data_file.path) + "'.",
                    UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME) from e
            # A temporary copy that cannot be written has no row of its own,
            # so it is any other error, as 51degrees-node writes it, with
            # the status that row of the table gives.
            raise DataUpdateException(
                self._unhandled_message(data_file),
                UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR) from e

        if data_file.create_temp_copy:
            try:
                shutil.move(filename, data_file.path)
            except (OSError, shutil.Error) as e:
                raise DataUpdateException(
                    "An error occurred when copying a data file to "
                    "replace the existing one at '" + data_file.path +
                    "'.",
                    UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME) from e

        # The file now on disk is the one this update loads, so the file
        # system watcher takes its time as seen rather than as a change to
        # load and report again.
        try:
            data_file.last_changed_time = os.stat(data_file.path).st_mtime
        except OSError:
            pass

    def _log_failed_check(self, data_file, error):
        # A check or a watched change that failed is logged with the message
        # of its row of the errors table and the error that caused it.
        if error.status == UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR:
            self._log_unhandled(data_file, error.__cause__)
        else:
            self._log_check_error(str(error), error.__cause__)

    def _refresh(self, data_file):
        # Refresh the engine from the data file after a check or a watched
        # change, trying again after a pause while the tries last, as the
        # file may still be in use. A failure of the last try raises a
        # DataUpdateException with the errors table's message for a refresh
        # from the data file.
        engine = self._engine_type(data_file)
        self._log(
            "info",
            "Attempting to refresh Engine '" + engine + "' with new data")
        tries = 0
        while True:
            tries += 1
            try:
                data_file.refresh()
                return
            except Exception as e:
                if tries >= self.REFRESH_TRIES:
                    raise DataUpdateException(
                        "An error occurred when applying a data update to "
                        "engine '" + engine + "' after " + str(tries) +
                        " tries.",
                        UpdateStatus.AUTO_UPDATE_REFRESH_FAILED) from e
            time.sleep(self.REFRESH_RETRY_PAUSE_SECONDS)

    def _wait_until_readable(self, path):
        # Open a changed watched file for reading, trying again after a
        # pause until the wait runs out, as a file still being copied may
        # not open. Answers whether the file opened.
        deadline = time.monotonic() + self.WATCHED_FILE_WAIT_SECONDS
        while True:
            try:
                with open(path, "rb"):
                    return True
            except OSError:
                if time.monotonic() >= deadline:
                    return False
            time.sleep(self.WATCHED_FILE_RETRY_PAUSE_SECONDS)

    def _refresh_from_memory(self, data_file):
        # Refresh the engine with data given to update_from_memory. A
        # failure is raised to the caller, not logged, with the errors
        # table's message for a refresh from data held in memory.
        engine = self._engine_type(data_file)
        self._log(
            "info",
            "Attempting to refresh Engine '" + engine + "' with new data")
        try:
            data_file.refresh()
        except Exception as e:
            raise DataUpdateException(
                "An error occurred when applying a data update to engine '" +
                engine + "'.",
                UpdateStatus.AUTO_UPDATE_REFRESH_FAILED) from e

    def _log_write_from_memory_failed(self, data_file, error):
        # The errors table's warning for data from memory that could not be
        # written. The detail is the error from the system, or the failure
        # itself when there is none, as with no temporary file path.
        cause = error.__cause__ if error.__cause__ is not None else error
        self._log(
            "warning",
            self._with_cause(
                "An error occurred when writing to '" + str(data_file.path) +
                "'. The engine will be updated to use the new data but the "
                "file on disk will still contain old data.", cause))

    def _refresh_from_bytes(self, data_file, data):
        # Refresh the engine of a data file kept on disk from the bytes, with
        # the data file in memory mode for this one refresh. The data file is
        # then kept on disk again, with the data it held before.
        download = data_file.download
        missing = object()
        previous = getattr(data_file, "data", missing)
        data_file.data = data
        data_file.download = False
        try:
            self._refresh_from_memory(data_file)
        finally:
            data_file.download = download
            if previous is missing:
                del data_file.data
            else:
                data_file.data = previous

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
            self._with_cause(self._unhandled_message(data_file), cause))

    def _unhandled_message(self, data_file):
        # The message of the errors table's last row, for any other error.
        return ("An unhandled error occurred while checking for automatic "
                "updates for engine '" + self._engine_type(data_file) + "'")

    @staticmethod
    def _with_cause(text, cause):
        # The cause may be a caller's error or a request's, either of which
        # can name the update URL, so every key in it is masked here rather
        # than at each call.
        if cause is None:
            return text
        return (text + ("" if text.endswith(".") else ".") +
                " Error detail: " + mask_licence_keys_in_text(cause))

    @staticmethod
    def _masked_error(error):
        # A copy of a request's error with every license key in its message
        # masked. The copy holds no request or response, so nothing in it
        # names the key.
        text = mask_licence_keys_in_text(error)
        try:
            return type(error)(text)
        except Exception:
            return requests.RequestException(text)

    @staticmethod
    def _cut_short(response):
        # The bytes received and the Content-Length, when fewer arrived than
        # it gave, or None. With a Content-Encoding the length counts the
        # encoded bytes and requests gives the decoded ones, so the two are
        # not compared.
        promised = response.headers.get("content-length")
        encoding = response.headers.get("content-encoding", "identity")
        if promised is None or encoding.strip().lower() != "identity":
            return None
        try:
            promised = int(promised)
        except ValueError:
            return None
        received = len(response.content)
        return (received, promised) if received < promised else None

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
        Non blocking check for new data, which update polling uses. The
        thread has no caller to pass a failure to, so a failure is logged
        with the message of its row of the errors table, and any other error
        with the last row's message, before it is reported to the callbacks.
        The next check is still scheduled.
        @type data_file: DataFile
        @param data_file: Datafile to update
        """

        thread = threading.Thread(name="Update service", target=self._update_data_file_caught, args=[data_file], daemon=True)
        thread.start()
        return thread

    def _update_data_file_caught(self, data_file):
        try:
            return self._check(data_file, to_caller=False)
        except Exception as e:
            self._log_unhandled(data_file, e)
            self._end_check(
                data_file, UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR)
            return False
    
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
            # The update on start-up logs and reports a failure as update
            # polling does.
            self._check(data_file, to_caller=False)

        elif data_file.auto_update:

            random_offset = random.randint(0, data_file.update_time_maximum_randomisation)

            interval = random_offset + (data_file.polling_interval * 60)
            until_expected = self._seconds_until_update_expected(data_file)
            if until_expected > 0:
                interval = until_expected + random_offset
            t = threading.Timer(interval, self.async_update_data_file, args=[data_file])
            t.daemon = True
            t.name = "AutoUpdate - Scheduled"
            # One check is pending for a data file, so the one already
            # waiting is cancelled, for example after a manual update.
            with self._lock:
                previous = getattr(data_file, "update_timer", None)
                if previous is not None:
                    previous.cancel()
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

        # The file system watcher runs on its own setting, whether or not
        # automatic updates are on. It downloads nothing, so it needs no
        # licence key.
        if data_file.file_system_watcher:
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
        event. It is first opened for reading, waiting up to
        WATCHED_FILE_WAIT_SECONDS for a copy still being made, and a file
        that does not open is reported as AUTO_UPDATE_TIMEOUT without a log
        entry. Otherwise the refresh takes the same route as the polling one,
        so the attempt is logged, a failure carries the errors table's
        message and level, and the result is reported to the update complete
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
            lock = self._update_lock(data_file)
            if data_file.updating or not lock.acquire(blocking=False):
                # A newer file found whilst an update is being applied is
                # reported as in progress, and the time is not taken, so
                # the next check looks at the file again.
                self.__emit(UpdateStatus.AUTO_UPDATE_IN_PROGRESS, data_file)
                return
            # The refresh holds the data file's update lock, so an update
            # asked for meanwhile waits for it, as it waits for another
            # update.
            try:
                data_file.updating = True
                try:
                    data_file.last_changed_time = changed_time
                    if self._wait_until_readable(data_file.path):
                        self._refresh(data_file)
                        status = UpdateStatus.AUTO_UPDATE_SUCCESS
                    else:
                        # The errors table's row for a watched file that
                        # could not be opened is not logged.
                        status = UpdateStatus.AUTO_UPDATE_TIMEOUT
                except DataUpdateException as e:
                    self._log_failed_check(data_file, e)
                    status = e.status
                finally:
                    data_file.updating = False
                self.__emit(status, data_file)
            finally:
                lock.release()
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

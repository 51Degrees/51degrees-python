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

import datetime
import gzip
import http.server
import os
import random
import shutil
import tempfile
import threading
import unittest
from email.utils import formatdate
from unittest import mock

import requests

from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService
from fiftyone_pipeline_engines.datafile_update_service import UpdateStatus

from .test_datafile_update_service import RecordingPipeline
from .test_datafile_update_service import ScheduledCheck

URL = "https://example.com/update"

# An update URL that carries a licence key, which no message may hold in
# full. Only its last four characters may be shown.
KEY = "ABCDEFGHIJKL"
KEYED_URL = "https://example.com/update?licenseKeys=" + KEY + "&Type=HashV41"
MASKED_URL = (
    "https://example.com/update?licenseKeys=********IJKL&Type=HashV41")


class FakeEngine:
    """Stands in for the flow element of a data file."""
    datakey = "fake"


class HttpDataFile:
    """Stands in for a data file that is kept in memory and updated over
    HTTP."""

    def __init__(self, path=None):
        self.flow_element = FakeEngine()
        self.identifier = "fake-data"
        self.update_on_start = False
        self.auto_update = False
        self.file_system_watcher = False
        self.updating = False
        self.verify_if_modified_since = True
        self.verify_md5 = False
        self.decompress = False
        self.download = False
        self.create_temp_copy = False
        self.polling_interval = 30
        self.update_time_maximum_randomisation = 0
        self.data = b"old"
        self.refreshed = []
        self.published = datetime.datetime(2026, 11, 3, 10, 30, 0)
        self.next_update = datetime.datetime(2026, 11, 3, 10, 30, 0)
        self.refresh_error = None
        self.url = URL
        if path is not None:
            self.path = path

    def get_update_url(self):
        return self.url

    def get_date_published(self):
        if isinstance(self.published, Exception):
            raise self.published
        return self.published

    def get_next_update(self):
        return self.next_update

    def refresh(self):
        if self.refresh_error:
            raise self.refresh_error
        self.refreshed.append(self.data)


class FileDataFile(HttpDataFile):
    """Stands in for a data file kept on disk, whose engine reads the file
    rather than the data held in memory, as the on-premise engines do."""

    def __init__(self, path):
        super(FileDataFile, self).__init__(path)
        self.download = True

    def refresh(self):
        if self.refresh_error:
            raise self.refresh_error
        with open(self.path, "rb") as file:
            self.data = file.read()
        self.refreshed.append(self.data)


def response(status, content=b"new"):
    reply = mock.Mock()
    reply.status_code = status
    reply.content = content
    reply.headers = {}
    return reply


# The entry an error from a row of the errors table is logged under, with
# the error, being the row's text and then its cause, after it, as .NET logs
# a DataUpdateException. The text is the one 51degrees-node writes.
CHECK_ERROR = "Error during check for data update. Error detail: "


class UpdateServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.pipeline = RecordingPipeline()
        self.service = DataFileUpdateService(self.pipeline)
        self.statuses = []
        self.service.on_complete(
            lambda status, data_file: self.statuses.append(status))
        self.data_file = HttpDataFile()
        self.pending = []

    def get(self, reply):
        """Replaces the HTTP request and keeps the headers it was sent."""
        self.sent = []

        def fake_get(url, headers=None, **kwargs):
            self.sent.append(headers)
            if isinstance(reply, Exception):
                raise reply
            return reply

        patch = mock.patch.object(requests, "get", fake_get)
        patch.start()
        self.addCleanup(patch.stop)

    def hold_timers(self):
        """Replaces the timers, which are kept in self.pending and never run."""
        timer = mock.patch.object(
            threading, "Timer",
            lambda interval, function, args=None: ScheduledCheck(
                self.pending, function, args or []))
        timer.start()
        self.addCleanup(timer.stop)


# If-Modified-Since is an HTTP date (RFC 9110 section 5.6.7), set to the
# publication date, or the file system last modified time without one.
class IfModifiedSinceTests(UpdateServiceTestCase):

    def testPublishedDateIsSentAsHttpDate(self):
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual(
            "Tue, 03 Nov 2026 10:30:00 GMT",
            self.sent[0]["If-Modified-Since"])

    def testLastModifiedTimeIsUsedWithoutPublishedDate(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "w") as file:
            file.write("x")
        os.utime(path, (1700000000, 1700000000))
        self.data_file = HttpDataFile(path)
        self.data_file.published = Exception("no published date")
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual(
            formatdate(1700000000, usegmt=True),
            self.sent[0]["If-Modified-Since"])
        self.assertEqual(
            "Tue, 14 Nov 2023 22:13:20 GMT",
            self.sent[0]["If-Modified-Since"])

    def testNoHeaderWhenDisabled(self):
        self.data_file.verify_if_modified_since = False
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertNotIn("If-Modified-Since", self.sent[0])


# Polling does not start until after the time the data update is expected,
# then waits the random offset as well.
class UpdateExpectedTimeTests(UpdateServiceTestCase):

    def setUp(self):
        super(UpdateExpectedTimeTests, self).setUp()
        self.intervals = []
        timer = mock.patch.object(
            threading, "Timer",
            lambda interval, function, args=None: self.record(interval))
        timer.start()
        self.addCleanup(timer.stop)
        randomise = mock.patch.object(random, "randint", lambda a, b: 5)
        randomise.start()
        self.addCleanup(randomise.stop)
        self.data_file.auto_update = True

    def record(self, interval):
        self.intervals.append(interval)
        return ScheduledCheck([], None, [])

    @staticmethod
    def utc_now():
        return datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=None)

    def testFirstCheckWaitsUntilExpectedTime(self):
        self.data_file.next_update = (
            self.utc_now() + datetime.timedelta(hours=2))
        self.service.register_data_file(self.data_file)
        self.assertEqual(1, len(self.intervals))
        self.assertAlmostEqual(7200 + 5, self.intervals[0], delta=10)

    def testPollingIntervalIsUsedOnceExpectedTimeHasPassed(self):
        self.data_file.next_update = (
            self.utc_now() - datetime.timedelta(hours=2))
        self.service.register_data_file(self.data_file)
        self.assertEqual([30 * 60 + 5], self.intervals)

    def testPlainDateOfTodayIsNotInTheFuture(self):
        self.data_file.next_update = datetime.date.today()
        self.service.register_data_file(self.data_file)
        self.assertEqual([30 * 60 + 5], self.intervals)


# A memory data file can be refreshed from the bytes given.
class UpdateFromMemoryTests(UpdateServiceTestCase):

    def testMemoryDataFileIsRefreshedFromTheBytes(self):
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, status)
        self.assertEqual(b"fresh", self.data_file.data)
        self.assertEqual([b"fresh"], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    def testFailedRefreshIsReportedAndLogged(self):
        self.data_file.refresh_error = Exception("boom")
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_REFRESH_FAILED, status)
        self.assertIn(
            ("error",
             CHECK_ERROR + "An error occurred when applying a data update "
             "to engine 'FakeEngine'. Error detail: boom"),
            self.pipeline.logs)

    def testFileDataFileIsWrittenThenRefreshed(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "wb") as file:
            file.write(b"old")
        self.data_file = FileDataFile(path)
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, status)
        with open(path, "rb") as file:
            self.assertEqual(b"fresh", file.read())
        self.assertEqual([b"fresh"], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    # The engine of a data file kept on disk reads that file, so a write
    # that failed leaves it with the data it had. The update ends with the
    # failure rather than reporting a success the engine did not have.
    def testAFailedWriteFromMemoryEndsTheUpdate(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "missing", "data.dat")
        self.data_file = FileDataFile(path)
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME, status)
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME], self.statuses)
        self.assertEqual(
            [], [message for level, message
                 in self.pipeline.logs if level == "warning"])
        self.assertTrue(
            [message for level, message in self.pipeline.logs
             if level == "error" and message.startswith(
                 CHECK_ERROR + "An error occurred when copying a data file "
                 "to replace the existing one at '" + path + "'.")],
            self.pipeline.logs)

    def testUnregisteredDataFileIsLeftAlone(self):
        self.service.unregister_data_file(self.data_file)
        self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual([], self.data_file.refreshed)


# The messages and levels are those of the .NET data update service, which
# the Errors table of the data updates specification follows.
class LoggingTests(UpdateServiceTestCase):

    def levels(self):
        return [level for level, message in self.pipeline.logs]

    def testSuccessfulUpdateLogsEachAction(self):
        self.get(response(200))
        self.service.update_data_file(self.data_file)
        self.assertEqual([
            ("info", "Checking for update"),
            ("info",
             "Checking for update from '" + URL + "' for Engine "
             "'FakeEngine'"),
            ("info",
             "Downloaded new data from '" + URL + "' for Engine "
             "'FakeEngine'"),
            ("info",
             "Attempting to refresh Engine 'FakeEngine' with new data"),
        ], self.pipeline.logs)

    def testNotModifiedIsInformationNotWarning(self):
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("info",
             "No data newer than Tue, 03 Nov 2026 10:30:00 GMT found at '"
             + URL + "' for Engine 'FakeEngine'"),
            self.pipeline.logs)
        for level in ("warn", "warning", "error"):
            self.assertNotIn(level, self.levels())

    def testTheErrorEntryIsWrittenExactly(self):
        # Written out in full, so a change to any character fails.
        self.get(response(403))
        self.service.update_data_file(self.data_file)
        self.get(requests.ConnectionError("boom"))
        self.service.update_data_file(self.data_file)
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(
            ["Error during check for data update. Error detail: Access "
             "denied to data update service at "
             "'https://example.com/update' for engine 'FakeEngine'",
             "Error during check for data update. Error detail: Error "
             "accessing data update service at "
             "'https://example.com/update' for engine 'FakeEngine'. "
             "Error detail: boom"],
            errors)

    def testRefusedDownloadIsError(self):
        self.get(response(403))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             CHECK_ERROR + "Access denied to data update service at '" +
             URL + "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_403_FORBIDDEN], self.statuses)

    def testTooManyRequestsIsError(self):
        self.get(response(429))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             CHECK_ERROR + "Too many requests to '" + URL +
             "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_429_TOO_MANY_ATTEMPTS],
            self.statuses)

    def testAnyOtherStatusNamesTheCode(self):
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(500))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             CHECK_ERROR + "HTTP status code '500' from data update service "
             "at '" + URL + "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)

    def testConnectionFailureIsError(self):
        self.get(requests.ConnectionError("boom"))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertIn(
            ("error",
             CHECK_ERROR + "Error accessing data update service at '" +
             URL + "' for engine 'FakeEngine'. Error detail: boom"),
            self.pipeline.logs)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)

    def testFailedRefreshIsError(self):
        self.get(response(200))
        self.data_file.refresh_error = Exception("boom")
        self.service.update_data_file(self.data_file)
        # A refresh after a check names the one try made, as the row for a
        # refresh from the data file does.
        self.assertIn(
            ("error",
             CHECK_ERROR + "An error occurred when applying a data update "
             "to engine 'FakeEngine' after 1 tries. Error detail: boom"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_REFRESH_FAILED], self.statuses)

    def testIntegrityCheckFailureIsError(self):
        reply = response(200)
        reply.headers = {"content-md5": "not the hash"}
        reply.iter_content = lambda size: [b"new"]
        self.get(reply)
        self.data_file.verify_md5 = True
        self.service.update_data_file(self.data_file)
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(1, len(errors), self.pipeline.logs)
        self.assertTrue(errors[0].startswith(
            CHECK_ERROR + "Integrity check failed. MD5 hash in HTTP response "
            "'not the hash' for 'FakeEngine'data update does not match "
            "calculated hash for the downloaded file '"), errors[0])
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_MD5_VALIDATION_FAILED],
            self.statuses)

    def testUpdateOnStartIsLogged(self):
        self.data_file.update_on_start = True
        self.data_file.updated_on_start = False
        with mock.patch.object(self.service, "update_data_file"):
            self.service.register_data_file(self.data_file)
        self.assertIn(("info", "Updating on start-up"), self.pipeline.logs)

    def testFileSystemWatcherIsLogged(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        data_file = HttpDataFile(os.path.join(folder, "data.dat"))
        with open(data_file.path, "w") as file:
            file.write("x")
        data_file.file_system_watcher = True
        self.hold_timers()
        self.service.register_data_file(data_file)
        self.assertIn(
            ("info", "Creating file system watcher"), self.pipeline.logs)


# A data file kept on disk that cannot put the new file in place, and one
# with no temporary file path, carry .NET's message and status.
class FileReplacementTests(UpdateServiceTestCase):

    def setUp(self):
        super(FileReplacementTests, self).setUp()
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.path = os.path.join(self.folder, "data.dat")
        with open(self.path, "w") as file:
            file.write("old")
        self.data_file = HttpDataFile(self.path)
        self.data_file.download = True
        self.data_file.create_temp_copy = True
        self.data_file.temp_directory = self.folder

    def testFailedCopyNamesThePath(self):
        move = mock.patch.object(
            shutil, "move",
            mock.Mock(side_effect=OSError("in use")))
        move.start()
        self.addCleanup(move.stop)
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME, status)
        self.assertIn(
            ("error",
             CHECK_ERROR + "An error occurred when copying a data file to "
             "replace the existing one at '" + self.path +
             "'. Error detail: in use"),
            self.pipeline.logs)

    def testNoTemporaryPathIsReported(self):
        self.data_file.temp_directory = None
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_TEMP_PATH_NOT_SET, status)
        self.assertIn(
            ("error",
             CHECK_ERROR + "The data file '" + self.data_file.identifier +
             "' is checking for updates but does not have a temporary "
             "file path configured."),
            self.pipeline.logs)


# A download is written to the data file's path and the engine then reads
# that file, so a write that failed leaves the engine with the data it had
# and the update ends there, as it does in .NET and 51degrees-node.
class DownloadedFileTests(UpdateServiceTestCase):

    def setUp(self):
        super(DownloadedFileTests, self).setUp()
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.path = os.path.join(self.folder, "data.dat")
        with open(self.path, "wb") as file:
            file.write(b"old")
        self.data_file = FileDataFile(self.path)

    def errors(self):
        return [message for level, message in self.pipeline.logs
                if level == "error"]

    def testADownloadedFileIsWrittenAndReadBackByTheEngine(self):
        self.get(response(200, b"new"))
        self.service.update_data_file(self.data_file)
        with open(self.path, "rb") as file:
            self.assertEqual(b"new", file.read())
        self.assertEqual([b"new"], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    def testAFailedWriteEndsTheUpdateAndLeavesTheEngineAlone(self):
        self.data_file = FileDataFile(
            os.path.join(self.folder, "missing", "data.dat"))
        self.get(response(200, b"new"))
        self.service.update_data_file(self.data_file)
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NEW_FILE_CANT_RENAME], self.statuses)
        self.assertTrue(
            [message for message in self.errors()
             if message.startswith(
                 CHECK_ERROR + "An error occurred when copying a data file "
                 "to replace the existing one at '" +
                 self.data_file.path + "'.")],
            self.pipeline.logs)

    def testAFailedTemporaryCopyIsAnyOtherError(self):
        self.data_file.create_temp_copy = True
        self.data_file.temp_directory = os.path.join(self.folder, "missing")
        self.get(response(200, b"new"))
        self.service.update_data_file(self.data_file)
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR], self.statuses)
        self.assertTrue(
            [message for message in self.errors()
             if message.startswith(
                 "An unhandled error occurred while checking for automatic "
                 "updates for engine 'FakeEngine'.")],
            self.pipeline.logs)
        with open(self.path, "rb") as file:
            self.assertEqual(b"old", file.read())


# Every check is reported to the update complete callbacks once it ends, and
# a check that needed no update is reported as not needed, as the Reporting
# each check section says and as .NET does. The watcher's checks are the
# changes it finds, as they are in .NET and 51degrees-node, so a look that
# finds the file untouched is not a check and is not reported.
class ReportingEachCheckTests(UpdateServiceTestCase):

    def testNotModifiedIsReportedAsNotNeeded(self):
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    # A watched file nobody has written to is not an event, so the watcher
    # reports nothing, as the watchers of .NET and 51degrees-node do. Both
    # are told by the operating system, where this one looks every ten
    # seconds, so reporting each look would tell every callback that no
    # update was needed six times a minute for ever.
    def testAnUnchangedWatchedFileIsNotReported(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "w") as file:
            file.write("x")
        data_file = HttpDataFile(path)
        data_file.last_changed_time = os.stat(path).st_mtime
        data_file.registered = True
        self.hold_timers()
        self.service.track_local_data_file_changes(data_file)
        self.service.track_local_data_file_changes(data_file)
        self.assertEqual([], self.statuses)
        self.assertEqual([], self.pipeline.logs)

    def testAWatcherEventWhilstUpdatingIsReportedAsInProgress(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "w") as file:
            file.write("x")
        data_file = HttpDataFile(path)
        data_file.last_changed_time = os.stat(path).st_mtime - 10
        data_file.registered = True
        data_file.updating = True
        self.hold_timers()
        self.service.track_local_data_file_changes(data_file)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_IN_PROGRESS], self.statuses)


# No message holds a licence key in full, as the Logging section of the data
# updates specification and the License keys section of logging.md say.
# A callback that raises stops the callbacks after it, as data-updates.md
# says, and its error is logged with .NET's message for any other error,
# with the error the callback raised attached. Polling carries on.
class CallbackTests(UpdateServiceTestCase):

    # The error the callback raised is attached, as the errors table asks
    # and as .NET, Node.js and Go each write it.
    UNHANDLED = ("An unhandled error occurred while checking for automatic "
                 "updates for engine 'FakeEngine'. Error detail: "
                 "callback failed")

    def fail_first(self):
        def fails(status, data_file):
            raise RuntimeError("callback failed")

        self.service.on_complete_methods.insert(0, fails)

    def errors(self):
        return [message for level, message in self.pipeline.logs
                if level == "error"]

    def testACallbackErrorOnPollingIsLoggedAndStopsTheCallbacks(self):
        self.fail_first()
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(304))
        self.service.async_update_data_file(self.data_file).join()
        self.assertEqual([], self.statuses)
        self.assertEqual(1, len(self.pending))
        self.assertEqual([self.UNHANDLED], self.errors())

    def testACallbackErrorOnAProgrammaticCheckIsLoggedAndStopsTheCallbacks(
            self):
        self.fail_first()
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual([], self.statuses)
        self.assertEqual(1, len(self.pending))
        self.assertEqual([self.UNHANDLED], self.errors())

    def testACallbackErrorOnAnUpdateFromMemoryIsLoggedAndStopsTheCallbacks(
            self):
        self.fail_first()
        self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual([], self.statuses)
        self.assertEqual([self.UNHANDLED], self.errors())

    def testAConnectionFailureKeepsPolling(self):
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(requests.ConnectionError("boom"))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)
        self.assertEqual(1, len(self.pending))


class LicenceKeyTests(UpdateServiceTestCase):

    def setUp(self):
        super(LicenceKeyTests, self).setUp()
        self.data_file.url = KEYED_URL

    def assertNoKey(self):
        self.assertTrue(self.pipeline.logs)
        for level, message in self.pipeline.logs:
            self.assertNotIn(KEY[:8], message)

    def testSuccessfulUpdateShowsOnlyTheMaskedKey(self):
        self.get(response(200))
        self.service.update_data_file(self.data_file)
        self.assertNoKey()
        self.assertIn(
            ("info",
             "Checking for update from '" + MASKED_URL + "' for Engine "
             "'FakeEngine'"),
            self.pipeline.logs)
        self.assertIn(
            ("info",
             "Downloaded new data from '" + MASKED_URL + "' for Engine "
             "'FakeEngine'"),
            self.pipeline.logs)

    def testEachFailedAnswerShowsOnlyTheMaskedKey(self):
        for status in (304, 403, 429, 500):
            self.pipeline.logs.clear()
            self.get(response(status))
            self.service.update_data_file(self.data_file)
            self.assertNoKey()
            self.assertTrue(any(MASKED_URL in message
                                for level, message in self.pipeline.logs),
                            status)

    def testFailedConnectionShowsOnlyTheMaskedKey(self):
        # The message of a failed request names the URL, masked.
        self.get(requests.ConnectionError("failed for url: " + KEYED_URL))
        self.service.update_data_file(self.data_file)
        self.assertNoKey()
        self.assertIn(
            ("error",
             CHECK_ERROR + "Error accessing data update service at '" +
             MASKED_URL + "' for engine 'FakeEngine'. Error detail: "
             "failed for url: " + MASKED_URL),
            self.pipeline.logs)


# A missing MD5 header, content that is not compressed and content that
# cannot be read each end as the data updates specification says, and the
# checks carry on.
class ContentTests(UpdateServiceTestCase):

    def testMissingMd5HeaderIsWarnedAndTheUpdateCarriesOn(self):
        self.data_file.verify_md5 = True
        self.data_file.url = KEYED_URL
        self.get(response(200))
        self.service.update_data_file(self.data_file)
        self.assertEqual([b"new"], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)
        self.assertIn(
            ("warning",
             "No MD5 hash included in data update response for '" +
             MASKED_URL + "'. Unable to verify data integrity"),
            self.pipeline.logs)

    def testCompressedContentIsDecompressed(self):
        self.data_file.decompress = True
        self.get(response(200, gzip.compress(b"new")))
        self.service.update_data_file(self.data_file)
        self.assertEqual([b"new"], self.data_file.refreshed)

    def testContentThatIsNotCompressedIsUsedAsItIs(self):
        self.data_file.decompress = True
        self.get(response(200, b"plain"))
        self.service.update_data_file(self.data_file)
        self.assertEqual([b"plain"], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    def testCorruptCompressedContentIsAnErrorAndCheckedAgainLater(self):
        self.data_file.decompress = True
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(200, gzip.compress(b"new")[:12]))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR], self.statuses)
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(1, len(errors), self.pipeline.logs)
        self.assertTrue(errors[0].startswith(
            "An unhandled error occurred while checking for automatic "
            "updates for engine 'FakeEngine'. Error detail: "), errors[0])
        self.assertEqual(1, len(self.pending))

    def testFailedMd5CheckOnStartUpIsNotRepeatedAtOnce(self):
        reply = response(200)
        reply.headers = {"content-md5": "not the hash"}
        reply.iter_content = lambda size: [b"new"]
        self.data_file.verify_md5 = True
        self.data_file.update_on_start = True
        self.data_file.updated_on_start = False
        self.hold_timers()
        self.get(reply)
        self.service.update_data_file(self.data_file)
        self.assertEqual(1, len(self.sent))
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_MD5_VALIDATION_FAILED],
            self.statuses)


# The bytes a short download sends, and how many it promises.
SENT = b"x" * 100
PROMISED = 1000


class ShortDownloadHandler(http.server.BaseHTTPRequestHandler):
    """Answers 200 and closes the connection before the whole file has been
    sent, with the length given in Content-Length or in chunks."""

    protocol_version = "HTTP/1.1"
    chunked = False

    def do_GET(self):
        self.send_response(200)
        if self.chunked:
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            # One chunk, then the connection closes with no last chunk.
            self.wfile.write(b"%x\r\n" % len(SENT) + SENT + b"\r\n")
        else:
            self.send_header("Content-Length", str(PROMISED))
            self.end_headers()
            self.wfile.write(SENT)
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, format, *args):
        pass


class ShortDownloadTests(unittest.TestCase):
    """A response that ends before the whole file arrived is reported as an
    error accessing the data update service, and the data in use is kept."""

    def serve(self, chunked):
        handler = type(
            "Handler", (ShortDownloadHandler,), {"chunked": chunked})
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:" + str(server.server_address[1]) + "/update"

    def check_short_download(self, chunked):
        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        statuses = []
        service.on_complete(lambda status, data_file: statuses.append(status))
        data_file = HttpDataFile()
        data_file.verify_if_modified_since = False
        data_file.url = self.serve(chunked)

        self.assertFalse(service.update_data_file(data_file))

        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], statuses)
        errors = [message for level, message in pipeline.logs
                  if level == "error"]
        self.assertTrue(
            any(message.startswith(
                CHECK_ERROR + "Error accessing data update service at '" +
                data_file.url + "' for engine 'FakeEngine'")
                for message in errors),
            errors)
        self.assertEqual(b"old", data_file.data)
        self.assertEqual([], data_file.refreshed)

    def testAResponseShorterThanItsContentLengthIsAnAccessError(self):
        self.check_short_download(chunked=False)

    def testTheLengthIsCheckedWhicheverHttpLibraryIsInstalled(self):
        # urllib3 before version 2 gives requests the bytes that arrived
        # with no error, so the service compares them with Content-Length
        # itself. A reply that holds fewer bytes stands in for that here.
        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        statuses = []
        service.on_complete(lambda status, data_file: statuses.append(status))
        data_file = HttpDataFile()
        reply = response(200, SENT)
        reply.headers = {"content-length": str(PROMISED)}
        with mock.patch.object(requests, "get", lambda url, **kwargs: reply):
            self.assertFalse(service.update_data_file(data_file))

        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], statuses)
        self.assertIn(
            ("error",
             CHECK_ERROR + "Error accessing data update service at '" + URL +
             "' for engine 'FakeEngine'. Error detail: The response ended "
             "after 100 of the 1000 bytes it gave as its Content-Length."),
            pipeline.logs)
        self.assertEqual(b"old", data_file.data)

    def testAResponseInAContentEncodingIsNotMeasured(self):
        # Content-Length counts the encoded bytes, and requests gives the
        # decoded ones, so the two are not compared.
        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        data_file = HttpDataFile()
        reply = response(200, SENT)
        reply.headers = {
            "content-length": str(PROMISED), "content-encoding": "gzip"}
        with mock.patch.object(requests, "get", lambda url, **kwargs: reply):
            self.assertTrue(service.update_data_file(data_file))
        self.assertEqual(SENT, data_file.data)

    def testAChunkedResponseCutShortIsAnAccessError(self):
        self.check_short_download(chunked=True)


class PolledCheckErrorTests(UpdateServiceTestCase):
    """!
    data-updates.md lines 474 to 477 and the last row of the errors table.
    A failure in a check started by update polling MUST be caught and logged
    with the unhandled error message, then reported to onUpdateCallbacks as
    AUTO_UPDATE_UNKNOWN_ERROR, and MUST NOT stop later checks, so a later
    good data file is still applied.
    """

    def setUp(self):
        super().setUp()
        self.data_file.auto_update = True
        self.hold_timers()
        self.failures = 1

        def update_url():
            if self.failures > 0:
                self.failures -= 1
                raise ValueError("the update URL could not be made")
            return URL

        self.data_file.get_update_url = update_url

    def poll(self):
        """Runs the check update polling starts, on its own thread."""
        self.service.async_update_data_file(self.data_file).join()

    def testAnErrorInAPolledCheckIsLoggedAndReported(self):
        self.poll()
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR], self.statuses)
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(1, len(errors), self.pipeline.logs)
        self.assertTrue(errors[0].startswith(
            "An unhandled error occurred while checking for automatic "
            "updates for engine 'FakeEngine'. Error detail: "), errors[0])
        self.assertIn("the update URL could not be made", errors[0])
        self.assertFalse(self.data_file.updating)

    def testTheNextPolledCheckStillAppliesAGoodFile(self):
        self.poll()
        self.assertEqual(1, len(self.pending))
        self.get(response(200))
        scheduled = self.pending.pop()
        scheduled.function(*scheduled.args).join()
        self.assertEqual([b"new"], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR,
             UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)


if __name__ == "__main__":
    unittest.main()

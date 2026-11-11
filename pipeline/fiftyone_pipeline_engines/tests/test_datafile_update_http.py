
import datetime
import gzip
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


def response(status, content=b"new"):
    reply = mock.Mock()
    reply.status_code = status
    reply.content = content
    reply.headers = {}
    return reply


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
             "An error occurred when applying a data update to engine "
             "'FakeEngine'"),
            self.pipeline.logs)

    def testFileDataFileIsWrittenThenRefreshed(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "wb") as file:
            file.write(b"old")
        self.data_file = HttpDataFile(path)
        self.data_file.download = True
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, status)
        with open(path, "rb") as file:
            self.assertEqual(b"fresh", file.read())
        self.assertEqual(1, len(self.data_file.refreshed))
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    # A write that fails whilst updating from memory is a warning, and the
    # Engine is still refreshed with the new data, as .NET does.
    def testFailedWriteIsAWarningAndTheEngineIsStillRefreshed(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "missing", "data.dat")
        self.data_file = HttpDataFile(path)
        self.data_file.download = True
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, status)
        self.assertEqual([b"fresh"], self.data_file.refreshed)
        self.assertEqual([], [message for level, message
                              in self.pipeline.logs if level == "error"])
        self.assertIn(
            ("warning",
             "An error occurred when writing to '" + path +
             "'. The engine will be updated to use the new data but the "
             "file on disk will still contain old data."),
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

    def testRefusedDownloadIsError(self):
        self.get(response(403))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             "Access denied to data update service at '" + URL +
             "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_403_FORBIDDEN], self.statuses)

    def testTooManyRequestsIsError(self):
        self.get(response(429))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             "Too many requests to '" + URL + "' for engine 'FakeEngine'"),
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
             "HTTP status code '500' from data update service at '" + URL +
             "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)

    def testConnectionFailureIsError(self):
        self.get(requests.ConnectionError("boom"))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertIn(
            ("error",
             "Error accessing data update service at '" + URL +
             "' for engine 'FakeEngine'"),
            self.pipeline.logs)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)

    def testFailedRefreshIsError(self):
        self.get(response(200))
        self.data_file.refresh_error = Exception("boom")
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             "An error occurred when applying a data update to engine "
             "'FakeEngine'"),
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
            "Integrity check failed. MD5 hash in HTTP response "
            "'not the hash' for 'FakeEngine' data update does not match "
            "calculated hash for the downloaded file '"), errors[0])
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_MD5_VALIDATION_FAILED],
            self.statuses)

    def testUpdateOnStartIsLogged(self):
        self.data_file.update_on_start = True
        self.data_file.updated_on_start = False
        with mock.patch.object(self.service, "update_data_file"):
            self.service.register_data_file(self.data_file)
        self.assertIn(("info", "Updating on startup"), self.pipeline.logs)

    def testFileSystemWatcherIsLogged(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        data_file = HttpDataFile(os.path.join(folder, "data.dat"))
        with open(data_file.path, "w") as file:
            file.write("x")
        data_file.file_system_watcher = True
        data_file.auto_update = True
        self.hold_timers()
        self.service.register_data_file(data_file)
        self.assertIn(
            ("info", "Creating file system watcher"), self.pipeline.logs)

    def testNoFileSystemWatcherWithoutAutomaticUpdates(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        data_file = HttpDataFile(os.path.join(folder, "data.dat"))
        with open(data_file.path, "w") as file:
            file.write("x")
        data_file.file_system_watcher = True
        data_file.auto_update = False
        self.hold_timers()
        self.service.register_data_file(data_file)
        self.assertNotIn(
            ("info", "Creating file system watcher"), self.pipeline.logs)
        self.assertEqual([], self.pending)
        self.assertIsNone(getattr(data_file, "watcher_timer", None))


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
             "An error occurred when copying a data file to replace the "
             "existing one at '" + self.path + "'."),
            self.pipeline.logs)

    def testNoTemporaryPathIsReported(self):
        self.data_file.temp_directory = None
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_TEMP_PATH_NOT_SET, status)
        self.assertIn(
            ("error",
             "The data file '" + self.data_file.identifier +
             "' is checking for updates but does not have a temporary "
             "file path configured."),
            self.pipeline.logs)


# Every check is reported to the update complete callbacks once it ends, and
# a check that needed no update is reported as not needed, as the Reporting
# each check section says and as .NET does.
class ReportingEachCheckTests(UpdateServiceTestCase):

    def testNotModifiedIsReportedAsNotNeeded(self):
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    def testAWatcherEventWithNothingToDoIsReportedAsNotNeeded(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "data.dat")
        with open(path, "w") as file:
            file.write("x")
        data_file = HttpDataFile(path)
        data_file.last_changed_time = os.stat(path).st_mtime
        data_file.registered = True
        self.service.on_complete(
            lambda status, df: None)
        self.hold_timers()
        self.service.track_local_data_file_changes(data_file)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

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
# A callback that raises is logged, and the other callbacks and the next
# check still run, so polling carries on.
class CallbackTests(UpdateServiceTestCase):

    def testACallbackThatRaisesDoesNotStopTheChecks(self):
        def fails(status, data_file):
            raise RuntimeError("callback failed")

        self.service.on_complete_methods.insert(0, fails)
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)
        self.assertEqual(1, len(self.pending))
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(1, len(errors), self.pipeline.logs)
        self.assertIn("callback failed", errors[0])

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
             "Error accessing data update service at '" + MASKED_URL +
             "' for engine 'FakeEngine'"),
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
        self.assertIn(
            ("error",
             "An unhandled error occurred while checking for automatic "
             "updates for engine 'FakeEngine'"),
            self.pipeline.logs)
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


if __name__ == "__main__":
    unittest.main()

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
             "An error occurred while applying a data file update to "
             "FakeEngine. Error detail: boom"),
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

    def testFailedWriteIsLoggedAndNotRefreshed(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "missing", "data.dat")
        self.data_file = HttpDataFile(path)
        self.data_file.download = True
        status = self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual(UpdateStatus.AUTO_UPDATE_ERR_READING_STREAM, status)
        self.assertEqual([], self.data_file.refreshed)
        errors = [message for level, message in self.pipeline.logs
                  if level == "error"]
        self.assertEqual(1, len(errors), self.pipeline.logs)
        self.assertTrue(errors[0].startswith(
            "An error occurred when writing to " + path +
            ". Error detail: "), errors[0])

    def testUnregisteredDataFileIsLeftAlone(self):
        self.service.unregister_data_file(self.data_file)
        self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual([], self.data_file.refreshed)


# The messages and levels are those of the Logging section of the data
# updates specification.
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

    def testRefusedDownloadIsWarning(self):
        self.get(response(403))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("warning",
             "An error occurred while downloading a data file update for "
             "FakeEngine from " + URL + ". Error detail: HTTP status code "
             "403"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_403_FORBIDDEN], self.statuses)

    def testAutomaticUpdateSaysItWillBeTriedAgain(self):
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(500))
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("warning",
             "An error occurred while downloading a data file update for "
             "FakeEngine from " + URL + ". Update will be attempted again "
             "later. Error detail: HTTP status code 500"),
            self.pipeline.logs)

    def testConnectionFailureIsWarning(self):
        self.get(requests.ConnectionError("boom"))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertIn(
            ("warning",
             "An error occurred when connecting to " + URL + " in order to "
             "check for data file updates for FakeEngine. Error detail: "
             "boom"),
            self.pipeline.logs)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_HTTPS_ERR], self.statuses)

    def testFailedRefreshIsError(self):
        self.get(response(200))
        self.data_file.refresh_error = Exception("boom")
        self.service.update_data_file(self.data_file)
        self.assertIn(
            ("error",
             "An error occurred while applying a data file update to "
             "FakeEngine. Error detail: boom"),
            self.pipeline.logs)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_REFRESH_FAILED], self.statuses)

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


# No message holds a licence key in full, as the Logging section of the data
# updates specification and the License keys section of logging.md say.
# A callback that raises stops the callbacks after it, as data-updates.md
# says, and its error is logged with .NET's message for any other error,
# with the error the callback raised attached. Polling carries on.
class CallbackTests(UpdateServiceTestCase):

    UNHANDLED = ("An unhandled error occurred while checking for automatic "
                 "updates for engine 'FakeEngine'")

    # The error the callback raised is attached, as the errors table asks
    # and as .NET, Java, Node.js and Go all write it.
    UNHANDLED_WITH_CAUSE = UNHANDLED + ". Error detail: callback failed"

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
        self.assertEqual([self.UNHANDLED_WITH_CAUSE], self.errors())

    def testACallbackErrorOnAProgrammaticCheckIsLoggedAndStopsTheCallbacks(
            self):
        self.fail_first()
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(304))
        self.service.update_data_file(self.data_file)
        self.assertEqual([], self.statuses)
        self.assertEqual(1, len(self.pending))
        self.assertEqual([self.UNHANDLED_WITH_CAUSE], self.errors())

    def testACallbackErrorOnAnUpdateFromMemoryIsLoggedAndStopsTheCallbacks(
            self):
        self.fail_first()
        self.service.update_from_memory(self.data_file, b"fresh")
        self.assertEqual([], self.statuses)
        self.assertEqual([self.UNHANDLED_WITH_CAUSE], self.errors())

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
        # The message of a failed request names the URL, key included.
        self.get(requests.ConnectionError("failed for url: " + KEYED_URL))
        self.service.update_data_file(self.data_file)
        self.assertNoKey()
        self.assertIn(
            ("warning",
             "An error occurred when connecting to " + MASKED_URL +
             " in order to check for data file updates for FakeEngine. "
             "Error detail: failed for url: " + MASKED_URL),
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

    def testCorruptCompressedContentIsWarnedAndCheckedAgainLater(self):
        self.data_file.decompress = True
        self.data_file.auto_update = True
        self.hold_timers()
        self.get(response(200, gzip.compress(b"new")[:12]))
        self.assertFalse(self.service.update_data_file(self.data_file))
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_ERR_READING_STREAM], self.statuses)
        warnings = [message for level, message in self.pipeline.logs
                    if level == "warning"]
        self.assertEqual(1, len(warnings), self.pipeline.logs)
        self.assertTrue(warnings[0].startswith(
            "An error occurred during the integrity check of new data file "
            "for FakeEngine. Update will be attempted again later. Error "
            "detail: "), warnings[0])
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

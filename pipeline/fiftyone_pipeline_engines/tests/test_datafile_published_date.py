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

"""A watched or downloaded file that is not newer than the data in use is
not loaded, and the check is reported as not needed, as the newFileAvailable
section of the data updates specification says. Whether a file is newer is
decided by the published date the engine reads in the file's header, not by
the file's modification time."""

import datetime
import os
import shutil
import tempfile
import time

from fiftyone_pipeline_engines.datafile_update_service import UpdateStatus

from .test_datafile_update_http import FileDataFile
from .test_datafile_update_http import UpdateServiceTestCase
from .test_datafile_update_http import response

# The day the data in use was published.
IN_USE = datetime.date(2026, 11, 3)
ONE_DAY = datetime.timedelta(days=1)

# A file the engine stands in for reads as this, then its published date.
HEADER = b"published "

# The message of the errors table's row for any other error.
UNHANDLED = ("An unhandled error occurred while checking for automatic "
             "updates for engine 'DatedEngine'")


def content(published):
    """The content of a data file published on the day given."""
    return HEADER + published.isoformat().encode()


class DatedEngine:
    """Stands in for an on-premise engine, which reads the published date in
    a data file's header. Here the header is the file's content."""
    datakey = "dated"

    def __init__(self):
        self.read = []

    def get_date_published_from_file(self, path):
        self.read.append(path)
        with open(path, "rb") as file:
            header = file.read()
        if not header.startswith(HEADER):
            raise ValueError("The file is not a data file.")
        return datetime.date.fromisoformat(header[len(HEADER):].decode())


class DatedDataFile(FileDataFile):
    """A data file kept on disk whose engine reads published dates."""

    def __init__(self, path):
        super(DatedDataFile, self).__init__(path)
        self.flow_element = DatedEngine()
        self.published = datetime.datetime.combine(IN_USE, datetime.time())


class PublishedDateTestCase(UpdateServiceTestCase):

    def setUp(self):
        super(PublishedDateTestCase, self).setUp()
        self.make_data_file()

    def make_data_file(self):
        """A data file in a folder of its own, whose file holds the data in
        use, with nothing reported for it yet."""
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.path = os.path.join(self.folder, "data.dat")
        self.old = content(IN_USE)
        with open(self.path, "wb") as file:
            file.write(self.old)
        self.data_file = DatedDataFile(self.path)
        self.engine = self.data_file.flow_element
        self.statuses.clear()

    def on_disk(self):
        with open(self.path, "rb") as file:
            return file.read()

    def errors(self):
        return [message for level, message in self.pipeline.logs
                if level == "error"]


# A downloaded file is compared with the data in use before it replaces the
# data file, whether it is written to a temporary copy or beside the data
# file, and one that is not newer is deleted.
class DownloadedFileTests(PublishedDateTestCase):

    def download(self, published, temp_copy):
        self.data_file.create_temp_copy = temp_copy
        self.temp_folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_folder, ignore_errors=True)
        self.data_file.temp_directory = self.temp_folder
        new = content(published)
        self.get(response(200, new))
        self.service.update_data_file(self.data_file)
        return new

    def assertNothingLeft(self):
        self.assertEqual(["data.dat"], os.listdir(self.folder))
        self.assertEqual([], os.listdir(self.temp_folder))

    def testALaterFileIsLoaded(self):
        for temp_copy in (True, False):
            with self.subTest(temp_copy=temp_copy):
                self.make_data_file()
                new = self.download(IN_USE + ONE_DAY, temp_copy)
                self.assertEqual(1, len(self.engine.read))
                self.assertNotEqual(self.path, self.engine.read[0])
                self.assertEqual(new, self.on_disk())
                self.assertEqual([new], self.data_file.refreshed)
                self.assertEqual(
                    [UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)
                self.assertNothingLeft()

    def testAFileOfTheSameOrAnEarlierDayIsNotLoaded(self):
        for published in (IN_USE, IN_USE - ONE_DAY):
            for temp_copy in (True, False):
                with self.subTest(published=published, temp_copy=temp_copy):
                    self.make_data_file()
                    self.download(published, temp_copy)
                    self.assertEqual(1, len(self.engine.read))
                    self.assertEqual(self.old, self.on_disk())
                    self.assertEqual([], self.data_file.refreshed)
                    self.assertEqual(
                        [UpdateStatus.AUTO_UPDATE_NOT_NEEDED],
                        self.statuses)
                    self.assertEqual([], self.errors())
                    self.assertNothingLeft()

    # The check that found nothing newer is followed by the next scheduled
    # check, as one that is answered 304 (Not modified) is.
    def testTheNextCheckIsScheduled(self):
        self.hold_timers()
        self.data_file.auto_update = True
        self.download(IN_USE, True)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)
        self.assertEqual(1, len(self.pending))

    # The If-Modified-Since request is kept, as it saves a download.
    def testIfModifiedSinceIsStillSent(self):
        self.download(IN_USE, True)
        self.assertEqual(
            "Tue, 03 Nov 2026 00:00:00 GMT",
            self.sent[0]["If-Modified-Since"])

    # A download whose header cannot be read is not loaded, and is any
    # other error.
    def testAFileWhoseHeaderCannotBeReadIsAnyOtherError(self):
        self.data_file.create_temp_copy = False
        self.get(response(200, b"cut"))
        self.poll()
        self.assertEqual(self.old, self.on_disk())
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR], self.statuses)
        self.assertEqual(
            [UNHANDLED + ". Error detail: The file is not a data file."],
            self.errors())
        self.assertEqual(["data.dat"], os.listdir(self.folder))

    # Before the engine has loaded data, as at the update on start-up, the
    # download is compared with the file already at the data file's path.
    def testWithNoDataInUseTheFileOnDiskIsComparedWith(self):
        self.data_file.published = AttributeError("engine")
        for published, loaded in (
                (IN_USE, False), (IN_USE + ONE_DAY, True)):
            with self.subTest(published=published):
                self.statuses.clear()
                self.data_file.refreshed.clear()
                self.download(published, False)
                self.assertEqual(loaded, bool(self.data_file.refreshed))
                self.assertEqual(
                    [UpdateStatus.AUTO_UPDATE_SUCCESS if loaded else
                     UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    # With no data in use and no file on disk, the download is loaded.
    def testWithNoDataInUseAndNoFileTheDownloadIsLoaded(self):
        self.data_file.published = AttributeError("engine")
        os.remove(self.path)
        new = self.download(IN_USE - ONE_DAY, True)
        self.assertEqual(new, self.on_disk())
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    # The header holds a day, so a time on the same day is the same day.
    def testDatesAreComparedByTheDay(self):
        self.data_file.published = datetime.datetime(
            2026, 11, 3, 23, 59, tzinfo=datetime.timezone.utc)
        self.download(IN_USE, True)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    # A time with a zone is the day it is in UTC.
    def testATimeWithAZoneIsTheDayInUtc(self):
        self.data_file.published = datetime.datetime(
            2026, 11, 2, 23, 0,
            tzinfo=datetime.timezone(-datetime.timedelta(hours=5)))
        self.download(IN_USE, True)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    # Data from memory cannot be compared, so it is loaded.
    def testDataKeptInMemoryIsLoadedWithoutComparing(self):
        self.data_file.download = False
        self.get(response(200, content(IN_USE)))
        self.service.update_data_file(self.data_file)
        self.assertEqual([], self.engine.read)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    # An engine that reads no published dates has every download loaded.
    def testAnEngineThatReadsNoDatesHasTheDownloadLoaded(self):
        self.data_file.flow_element = object()
        new = self.download(IN_USE - ONE_DAY, False)
        self.assertEqual(new, self.on_disk())
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)


# A watched file is loaded only when its header gives a later day than the
# data in use, whatever its modification time.
class WatchedFileTests(PublishedDateTestCase):

    def setUp(self):
        super(WatchedFileTests, self).setUp()
        self.hold_timers()
        self.data_file.file_system_watcher = True
        self.stamp = time.time()
        self.service.register_data_file(self.data_file)

    def replace(self, data):
        with open(self.path, "wb") as file:
            file.write(data)
        # Later than any time the watcher has seen, however coarse the clock.
        self.stamp += 10
        os.utime(self.path, (self.stamp, self.stamp))

    def run_next_check(self):
        check = self.pending.pop(0)
        check.function(*check.args)

    def testALaterFileIsLoaded(self):
        new = content(IN_USE + ONE_DAY)
        self.replace(new)
        self.run_next_check()
        self.assertEqual([self.path], self.engine.read)
        self.assertEqual([new], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

    def testAFileOfTheSameOrAnEarlierDayIsNotLoaded(self):
        for published in (IN_USE, IN_USE - ONE_DAY):
            with self.subTest(published=published):
                self.statuses.clear()
                self.engine.read.clear()
                self.replace(content(published))
                self.run_next_check()
                self.assertEqual([self.path], self.engine.read)
                self.assertEqual([], self.data_file.refreshed)
                self.assertEqual(
                    [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)
                self.assertEqual([], self.errors())
                self.assertEqual(1, len(self.pending))

                # The file's time is taken, so it is not checked again.
                self.run_next_check()
                self.assertEqual(
                    [UpdateStatus.AUTO_UPDATE_NOT_NEEDED], self.statuses)

    def testAFileWhoseHeaderCannotBeReadIsAnyOtherError(self):
        self.replace(b"cut")
        self.run_next_check()
        self.assertEqual([], self.data_file.refreshed)
        self.assertEqual(
            [UpdateStatus.AUTO_UPDATE_UNKNOWN_ERROR], self.statuses)
        self.assertEqual(
            [UNHANDLED + ". Error detail: The file is not a data file."],
            self.errors())
        self.assertEqual(1, len(self.pending))

        # A later good file is still loaded.
        new = content(IN_USE + ONE_DAY)
        self.replace(new)
        self.run_next_check()
        self.assertEqual([new], self.data_file.refreshed)

    def testWithNoDataInUseTheWatchedFileIsLoaded(self):
        self.data_file.published = AttributeError("engine")
        new = content(IN_USE)
        self.replace(new)
        self.run_next_check()
        self.assertEqual([new], self.data_file.refreshed)
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], self.statuses)

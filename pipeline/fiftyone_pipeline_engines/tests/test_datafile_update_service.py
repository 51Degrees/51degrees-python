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

import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock

from fiftyone_pipeline_engines import datafile_update_service
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService
from fiftyone_pipeline_engines.datafile_update_service import UpdateStatus


def read(path):
    with open(path) as file:
        return file.read()


class RecordingPipeline:
    """Stands in for a pipeline and keeps each message logged."""

    def __init__(self):
        self.logs = []

    def log(self, level, message):
        self.logs.append((level, message))


class StandInDataFile:
    """Stands in for the data file of an engine that keeps the data it has
    when a refresh fails. It counts the refreshes asked for, and fails the
    number of them given by failures_left before reading the file."""

    def __init__(self, path):
        self.path = path
        self.update_on_start = False
        self.auto_update = False
        self.file_system_watcher = True
        self.updating = False
        self.data = read(path)
        self.refreshes = 0
        self.failures_left = 0

    def refresh(self):
        self.refreshes += 1
        if self.failures_left > 0:
            self.failures_left -= 1
            raise Exception("The data file is in use.")
        content = read(self.path)
        if not content.startswith("version"):
            raise Exception("The data file cannot be used.")
        self.data = content


class ScheduledCheck:
    """Takes the place of a threading.Timer and waits to be run by the test."""

    def __init__(self, pending, function, args):
        self.pending = pending
        self.function = function
        self.args = args
        self.cancelled = False

    def start(self):
        self.pending.append(self)

    def cancel(self):
        self.cancelled = True
        if self in self.pending:
            self.pending.remove(self)


class FileSystemWatcherTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "data.dat")
        self.stamp = time.time()
        self.write("version 1")
        self.pipeline = RecordingPipeline()
        self.service = DataFileUpdateService(self.pipeline)
        # A refresh that fails is tried again without the pause, so the
        # tests of failures take no longer than the others.
        self.service.REFRESH_RETRY_PAUSE_SECONDS = 0
        self.statuses = []
        self.service.on_complete(
            lambda status, data_file: self.statuses.append(status))
        self.pending = []
        # The test runs each check the watcher schedules, one at a time.
        timer = mock.patch.object(
            threading, "Timer",
            lambda interval, function, args=None: ScheduledCheck(
                self.pending, function, args or []))
        timer.start()
        self.addCleanup(timer.stop)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def write(self, content):
        with open(self.path, "w") as file:
            file.write(content)
        # Later than any time the watcher has seen, however coarse the clock.
        self.stamp += 10
        os.utime(self.path, (self.stamp, self.stamp))

    def run_next_check(self):
        check = self.pending.pop(0)
        check.function(*check.args)

    # The watcher runs on its own setting, whether or not automatic updates
    # are on. Watching a file downloads nothing, so a data file with no
    # licence key, whose automatic updates are off, is still watched.
    def testTheWatcherRunsOnItsOwnSetting(self):
        for name, automatic, watcher in (
                ("watcher on, automatic updates on", True, True),
                ("watcher on, automatic updates off", False, True),
                ("watcher off, automatic updates on", True, False)):
            with self.subTest(name):
                self.write("version 1")
                self.pending.clear()
                pipeline = RecordingPipeline()
                service = DataFileUpdateService(pipeline)
                data_file = StandInDataFile(self.path)
                data_file.auto_update = automatic
                data_file.file_system_watcher = watcher
                data_file.polling_interval = 30
                data_file.update_time_maximum_randomisation = 0
                service.register_data_file(data_file)

                watches = [
                    check for check in self.pending
                    if check.function == service.track_local_data_file_changes]
                self.assertEqual(1 if watcher else 0, len(watches), name)
                self.assertEqual(
                    watcher,
                    ("info", "Creating file system watcher") in pipeline.logs,
                    name)

                self.write("version 2")
                for check in watches:
                    check.function(*check.args)
                self.assertEqual(
                    "version 2" if watcher else "version 1", data_file.data,
                    name)
                service.unregister_data_file(data_file)

    # A refresh that fails is logged and reported, the data in use is kept,
    # and a later good file is picked up.
    def testFileSystemWatcherKeepsWatchingAfterFailedRefresh(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)

        self.write("unusable")
        self.run_next_check()
        self.assertEqual("version 1", data_file.data)
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_REFRESH_FAILED, self.statuses[-1])
        errors = [log for log in self.pipeline.logs if log[0] == "error"]
        self.assertEqual(1, len(errors))
        self.assertIn(
            "Error during check for data update. Error detail: An error "
            "occurred when applying a data update to engine 'StandInDataFile' "
            "after 10 tries.",
            errors[0][1])
        self.assertEqual(1, len(self.pending))

        self.write("version 2")
        self.run_next_check()
        self.assertEqual("version 2", data_file.data)

    # The watcher's refresh takes the same route as the polling one, so it
    # logs the attempt, uses the table's failure message and level, and
    # reports success to the update complete callbacks.
    def testFileSystemWatcherRefreshIsRoutedAsPollingIs(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)

        self.write("version 2")
        self.run_next_check()

        self.assertEqual("version 2", data_file.data)
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, self.statuses[-1])
        attempts = [log for log in self.pipeline.logs
                    if "Attempting to refresh Engine" in log[1]]
        self.assertEqual(1, len(attempts))
        self.assertEqual("info", attempts[0][0])

    # A refresh that fails from the watcher carries the message and level of
    # the specification's errors table, as the polling route's does, after
    # the ten tries the table's row names.
    def testFileSystemWatcherFailedRefreshUsesTheTableMessage(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)

        self.write("unusable")
        self.run_next_check()

        self.assertEqual(10, data_file.refreshes)
        errors = [log for log in self.pipeline.logs if log[0] == "error"]
        self.assertEqual(1, len(errors))
        self.assertIn(
            "Error during check for data update. Error detail: An error "
            "occurred when applying a data update to engine 'StandInDataFile' "
            "after 10 tries.",
            errors[0][1])

    # A refresh that fails is tried again, so a file the engine could not
    # yet use is still taken up within the ten tries, with nothing logged
    # but the attempt.
    def testARefreshThatFailsIsTriedAgain(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)
        data_file.failures_left = 2

        self.write("version 2")
        self.run_next_check()

        self.assertEqual("version 2", data_file.data)
        self.assertEqual(3, data_file.refreshes)
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, self.statuses[-1])
        self.assertEqual(
            [], [log for log in self.pipeline.logs if log[0] == "error"])

    # Each try that fails, apart from the last, is followed by a pause of
    # 200 milliseconds, as .NET's data update service makes.
    def testFailedTriesArePaused(self):
        del self.service.REFRESH_RETRY_PAUSE_SECONDS
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)

        self.write("unusable")
        with mock.patch("time.sleep") as sleep:
            self.run_next_check()

        self.assertEqual([mock.call(0.2)] * 9, sleep.call_args_list)

    # A watched file that cannot be opened for reading, for example because
    # it is still being copied, is tried every half second for ten minutes.
    # Then the check ends as AUTO_UPDATE_TIMEOUT, with nothing logged and
    # no refresh, and the watcher goes on watching.
    def testAWatchedFileThatCannotBeOpenedTimesOut(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)
        opened = []

        def in_use(*args, **kwargs):
            opened.append(args[0])
            raise PermissionError("in use")

        # The clock reads 0 when the wait starts, and then the times of the
        # second, third and fourth tries.
        clock = iter((0, 300, 599.9, 600))
        self.write("version 2")
        with mock.patch.object(
                datafile_update_service, "open", in_use, create=True), \
                mock.patch("time.monotonic", lambda: next(clock)), \
                mock.patch("time.sleep") as sleep:
            self.run_next_check()

        self.assertEqual([self.path] * 3, opened)
        self.assertEqual([mock.call(0.5)] * 2, sleep.call_args_list)
        self.assertEqual("version 1", data_file.data)
        self.assertEqual(0, data_file.refreshes)
        self.assertEqual(UpdateStatus.AUTO_UPDATE_TIMEOUT, self.statuses[-1])
        self.assertEqual(14, UpdateStatus.AUTO_UPDATE_TIMEOUT.value)
        self.assertEqual([], [
            log for log in self.pipeline.logs if log[0] != "info"])
        self.assertEqual(1, len(self.pending))

    # A watched file is refreshed as soon as it can be opened for reading.
    def testAWatchedFileIsReadOnceItCanBeOpened(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)
        opened = []

        def in_use_twice(*args, **kwargs):
            opened.append(args[0])
            if len(opened) < 3:
                raise PermissionError("in use")
            return open(*args, **kwargs)

        self.write("version 2")
        with mock.patch.object(
                datafile_update_service, "open", in_use_twice, create=True), \
                mock.patch("time.sleep"):
            self.run_next_check()

        self.assertEqual(3, len(opened))
        self.assertEqual("version 2", data_file.data)
        self.assertEqual(UpdateStatus.AUTO_UPDATE_SUCCESS, self.statuses[-1])

    # A file that is missing at a check, for example part way through being
    # replaced, is looked for again at the next check.
    def testFileSystemWatcherKeepsWatchingWhileFileIsMissing(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)

        os.remove(self.path)
        self.run_next_check()
        self.assertEqual(1, len(self.pending))

        self.write("version 2")
        self.run_next_check()
        self.assertEqual("version 2", data_file.data)
        self.assertNotIn(
            UpdateStatus.AUTO_UPDATE_REFRESH_FAILED, self.statuses)

    # Unregistering, as closing the engine does, cancels the next check, and
    # a check already running neither refreshes nor schedules another, so
    # nothing is left holding the data file.
    def testUnregisterStopsFileSystemWatcher(self):
        data_file = StandInDataFile(self.path)
        self.service.register_data_file(data_file)
        check = self.pending[0]

        self.service.unregister_data_file(data_file)
        self.assertTrue(check.cancelled)
        self.assertEqual(0, len(self.pending))

        self.write("version 2")
        check.function(*check.args)
        self.assertEqual("version 1", data_file.data)
        self.assertEqual(0, len(self.pending))

    # Unregistering cancels the next automatic update, and an update that
    # starts afterwards does nothing.
    def testUnregisterStopsAutomaticUpdates(self):
        data_file = StandInDataFile(self.path)
        data_file.file_system_watcher = False
        data_file.auto_update = True
        data_file.polling_interval = 30
        data_file.update_time_maximum_randomisation = 0
        self.service.register_data_file(data_file)
        check = self.pending[0]

        self.service.unregister_data_file(data_file)
        self.assertTrue(check.cancelled)
        self.assertEqual(0, len(self.pending))
        self.assertFalse(self.service.update_data_file(data_file))


if __name__ == "__main__":
    unittest.main()

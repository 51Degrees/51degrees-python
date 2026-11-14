
"""
An update of a data file waits for one that is running and then makes its own
check, so every check ends and is reported, and one data file has one chain
of scheduled checks.
"""

import os
import tempfile
import threading
import unittest
from unittest import mock

import requests

from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService

from .test_datafile_update_service import RecordingPipeline

URL = "https://example.com/update"
# The longest a test waits for another thread.
WAIT_SECONDS = 10
# How long a test gives an update that should be waiting to show that it is.
# An update that does not wait has made its request and ended well within it.
STILL_WAITING_SECONDS = 0.5


class FakeEngine:
    datakey = "fake"


class MemoryDataFile:
    """Stands in for a data file that is kept in memory and updated over
    HTTP."""

    def __init__(self):
        self.flow_element = FakeEngine()
        self.identifier = "fake-data"
        self.update_on_start = False
        self.auto_update = True
        self.file_system_watcher = False
        self.updating = False
        self.verify_if_modified_since = False
        self.verify_md5 = False
        self.decompress = False
        self.download = False
        self.create_temp_copy = False
        self.polling_interval = 30
        self.update_time_maximum_randomisation = 0
        self.data = b"old"

    def get_update_url(self):
        return URL

    def get_next_update(self):
        return None

    def refresh(self):
        self.refreshes = getattr(self, "refreshes", 0) + 1


def answer(status):
    reply = mock.Mock()
    reply.status_code = status
    reply.content = b"new"
    reply.headers = {}
    return reply


class FakeTimer:

    def __init__(self, timers, interval, function, args):
        self.cancelled = False
        self.daemon = False
        self.name = ""
        self.timers = timers
        timers.append(self)

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True

    @property
    def live(self):
        return not self.cancelled


class UpdateGuardTests(unittest.TestCase):

    def setUp(self):
        self.pipeline = RecordingPipeline()
        self.service = DataFileUpdateService(self.pipeline)
        self.data_file = MemoryDataFile()
        self.timers = []
        timer = mock.patch.object(
            threading, "Timer",
            lambda interval, function, args=None: FakeTimer(
                self.timers, interval, function, args))
        timer.start()
        self.addCleanup(timer.stop)

    def live(self):
        return [timer for timer in self.timers if timer.live]

    def start_blocked_update(self, calls, statuses):
        # Starts an update whose request waits until the event returned is
        # set, and returns once that request has been made. Each request
        # adds whether the data file was updating to calls, and each report
        # adds its status to statuses.
        started = threading.Event()
        release = threading.Event()

        def get(url, headers=None, **kwargs):
            calls.append(self.data_file.updating)
            if len(calls) == 1:
                started.set()
                release.wait(WAIT_SECONDS)
            return answer(200)

        self.service.on_complete(
            lambda status, data_file: statuses.append(status))
        patch = mock.patch.object(requests, "get", get)
        patch.start()
        self.addCleanup(patch.stop)
        # A test that fails before it releases the request still lets the
        # thread end.
        self.addCleanup(release.set)
        first = threading.Thread(
            target=self.service.update_data_file, args=[self.data_file])
        first.start()
        self.assertTrue(started.wait(WAIT_SECONDS))
        return first, release

    def test_a_second_update_waits_for_the_first_then_makes_its_own_check(self):
        calls = []
        statuses = []
        results = []
        first, release = self.start_blocked_update(calls, statuses)
        second = threading.Thread(
            target=lambda: results.append(
                self.service.update_data_file(self.data_file)))
        second.start()
        second.join(STILL_WAITING_SECONDS)
        self.assertTrue(second.is_alive())
        self.assertEqual(1, len(calls))
        release.set()
        first.join(WAIT_SECONDS)
        second.join(WAIT_SECONDS)

        self.assertEqual(2, len(calls))
        self.assertEqual([True], results)
        self.assertEqual(2, len(statuses))

    def test_updating_is_set_while_an_update_runs(self):
        calls = []
        first, release = self.start_blocked_update(calls, [])
        self.assertTrue(self.data_file.updating)
        release.set()
        first.join(WAIT_SECONDS)
        self.assertEqual([True], calls)
        self.assertFalse(self.data_file.updating)

    def test_an_update_from_memory_waits_for_a_running_update(self):
        first, release = self.start_blocked_update([], [])
        results = []
        memory = threading.Thread(
            target=lambda: results.append(
                self.service.update_from_memory(self.data_file, b"given")))
        memory.start()
        memory.join(STILL_WAITING_SECONDS)
        self.assertTrue(memory.is_alive())
        self.assertEqual(0, getattr(self.data_file, "refreshes", 0))
        release.set()
        first.join(WAIT_SECONDS)
        memory.join(WAIT_SECONDS)

        self.assertEqual(2, self.data_file.refreshes)
        self.assertEqual(b"given", self.data_file.data)
        self.assertEqual(1, len(results))

    def test_an_update_waits_for_a_file_system_watcher_refresh(self):
        # A data file on disk that the watcher finds changed, whose refresh
        # waits until the test lets it go.
        handle, path = tempfile.mkstemp()
        os.close(handle)
        self.addCleanup(os.remove, path)
        self.data_file.path = path
        self.data_file.last_changed_time = 0
        refreshing = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)

        def refresh():
            refreshing.set()
            release.wait(WAIT_SECONDS)

        self.data_file.refresh = refresh
        calls = []
        patch = mock.patch.object(
            requests, "get",
            lambda *a, **k: calls.append(self.data_file.updating) or
            answer(304))
        patch.start()
        self.addCleanup(patch.stop)

        watcher = threading.Thread(
            target=self.service.track_local_data_file_changes,
            args=[self.data_file])
        watcher.start()
        self.assertTrue(refreshing.wait(WAIT_SECONDS))
        self.assertTrue(self.data_file.updating)
        update = threading.Thread(
            target=self.service.update_data_file, args=[self.data_file])
        update.start()
        update.join(STILL_WAITING_SECONDS)
        self.assertTrue(update.is_alive())
        self.assertEqual([], calls)
        release.set()
        watcher.join(WAIT_SECONDS)
        update.join(WAIT_SECONDS)

        self.assertEqual([True], calls)
        self.assertFalse(self.data_file.updating)

    def test_updating_is_clear_after_an_update_so_the_next_one_runs(self):
        with mock.patch.object(requests, "get", lambda *a, **k: answer(200)):
            self.assertTrue(self.service.update_data_file(self.data_file))
            self.assertFalse(self.data_file.updating)
            self.assertTrue(self.service.update_data_file(self.data_file))

    def test_updating_is_clear_after_an_error(self):
        def fail(*args, **kwargs):
            raise RuntimeError("boom")

        with mock.patch.object(requests, "get", fail):
            with self.assertRaises(RuntimeError):
                self.service.update_data_file(self.data_file)
        self.assertFalse(self.data_file.updating)

    def test_a_manual_update_leaves_one_pending_check(self):
        self.service.register_data_file(self.data_file)
        self.assertEqual(1, len(self.live()))
        with mock.patch.object(requests, "get", lambda *a, **k: answer(304)):
            self.service.update_data_file(self.data_file)
        self.assertEqual(2, len(self.timers))
        self.assertEqual(1, len(self.live()))
        self.assertTrue(self.timers[0].cancelled)

    def test_polling_carries_on_after_a_manual_update(self):
        self.service.register_data_file(self.data_file)
        with mock.patch.object(requests, "get", lambda *a, **k: answer(200)):
            self.service.update_data_file(self.data_file)
        self.assertEqual(1, len(self.live()))
        self.assertIs(self.live()[0], self.data_file.update_timer)

    def test_unregistering_cancels_every_pending_check(self):
        self.service.register_data_file(self.data_file)
        with mock.patch.object(requests, "get", lambda *a, **k: answer(200)):
            self.service.update_data_file(self.data_file)
        self.service.unregister_data_file(self.data_file)
        self.assertEqual([], self.live())


if __name__ == "__main__":
    unittest.main()


"""
An update does not start while another is running, and one data file has one
chain of scheduled checks, as the data updates specification asks of a
refresh mechanism that MUST be thread safe.
"""

import threading
import unittest
from unittest import mock

import requests

from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService

from .test_datafile_update_service import RecordingPipeline

URL = "https://example.com/update"


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
        pass


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

    def test_an_update_does_not_start_while_another_is_running(self):
        started = threading.Event()
        release = threading.Event()
        calls = []

        def get(url, headers=None, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                started.set()
                release.wait(10)
            return answer(200)

        results = []
        with mock.patch.object(requests, "get", get):
            first = threading.Thread(
                target=lambda: results.append(
                    self.service.update_data_file(self.data_file)))
            first.start()
            self.assertTrue(started.wait(10))
            second = self.service.update_data_file(self.data_file)
            release.set()
            first.join(10)

        self.assertFalse(second)
        self.assertEqual(1, len(calls))
        self.assertEqual([True], results)

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

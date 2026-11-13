
"""
One thread at a time reads a native results instance, because reading a value
writes into the results.
"""

import threading
import time
import unittest

from fiftyone_ipintelligence_onpremise.swig_data import SwigData


class Value:

    def hasValue(self):
        return True

    def getValue(self):
        return 5


# How long a stand-in read takes, long enough that overlapping reads are seen.
READ_SECONDS = 0.02
# The longest a test waits for another thread.
WAIT_SECONDS = 10
# How long closing is given while a read holds the results. It must still be
# waiting at the end.
BLOCKED_SECONDS = 0.2

KEY = "count"
VALUE = 5


class OverlapCountingResults:
    """Stands in for the native results and records how many reads overlap."""

    def __init__(self):
        self.guard = threading.Lock()
        self.active = 0
        self.most_active = 0

    def getValueAsInteger(self, name):
        with self.guard:
            self.active += 1
            self.most_active = max(self.most_active, self.active)
        time.sleep(READ_SECONDS)
        with self.guard:
            self.active -= 1
        return Value()


class BlockingResults:
    """Stands in for the native results with a read that waits to be let go,
    so a test can act while the read is in progress."""

    def __init__(self):
        self.reading = threading.Event()
        self.release = threading.Event()

    def getValueAsInteger(self, name):
        self.reading.set()
        self.release.wait(WAIT_SECONDS)
        return Value()


class FakeElement:
    datakey = "ip"
    properties = {"count": {"name": "Count", "type": "int"}}


class SwigDataThreadTests(unittest.TestCase):

    def test_reads_from_several_threads_do_not_overlap(self):
        results = OverlapCountingResults()
        data = SwigData(FakeElement(), results)
        errors = []

        def read():
            try:
                for _ in range(3):
                    data.get("count")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertEqual(1, results.most_active)

    def test_closing_waits_for_a_read_in_progress(self):
        results = BlockingResults()
        data = SwigData(FakeElement(), results)
        values = []
        reader = threading.Thread(
            target=lambda: values.append(data.get(KEY)))
        reader.start()
        self.assertTrue(results.reading.wait(WAIT_SECONDS))

        closer = threading.Thread(target=data.close)
        closer.start()
        closer.join(BLOCKED_SECONDS)
        # The read holds the results, so closing waits for it.
        self.assertTrue(closer.is_alive())

        results.release.set()
        reader.join(WAIT_SECONDS)
        closer.join(WAIT_SECONDS)
        self.assertFalse(closer.is_alive())
        self.assertEqual([VALUE], [value.value() for value in values])
        self.assertIsNone(data.swig_results)
        with self.assertRaises(Exception):
            data.get(KEY)


if __name__ == "__main__":
    unittest.main()

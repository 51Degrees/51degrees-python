
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
        time.sleep(0.02)
        with self.guard:
            self.active -= 1
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
        results = OverlapCountingResults()
        data = SwigData(FakeElement(), results)
        reader = threading.Thread(target=lambda: data.get("count"))
        reader.start()
        time.sleep(0.005)
        data.close()
        reader.join()
        self.assertIsNone(data.swig_results)
        with self.assertRaises(Exception):
            data.get("count")


if __name__ == "__main__":
    unittest.main()

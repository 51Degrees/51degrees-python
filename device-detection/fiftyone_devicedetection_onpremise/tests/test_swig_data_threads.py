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

"""
One thread at a time reads a native results instance, because reading a value
writes into the results.
"""

import threading
import time
import unittest

from fiftyone_devicedetection_onpremise.swig_data import SwigData


# How long a stand-in read takes, long enough that overlapping reads are seen.
READ_SECONDS = 0.02
# The longest a test waits for another thread.
WAIT_SECONDS = 10
# How long closing is given while a read holds the results. It must still be
# waiting at the end.
BLOCKED_SECONDS = 0.2

KEY = "deviceid"
VALUE = "1-2-3"


class OverlapCountingResults:
    """Stands in for the native results and records how many reads overlap."""

    def __init__(self):
        self.guard = threading.Lock()
        self.active = 0
        self.most_active = 0

    def getDeviceId(self):
        with self.guard:
            self.active += 1
            self.most_active = max(self.most_active, self.active)
        time.sleep(READ_SECONDS)
        with self.guard:
            self.active -= 1
        return "1-2-3"


class BlockingResults:
    """Stands in for the native results with a read that waits to be let go,
    so a test can act while the read is in progress."""

    def __init__(self):
        self.reading = threading.Event()
        self.release = threading.Event()

    def getDeviceId(self):
        self.reading.set()
        self.release.wait(WAIT_SECONDS)
        return "1-2-3"


class FakeElement:
    datakey = "device"
    properties = {}


class SwigDataThreadTests(unittest.TestCase):

    def test_reads_from_several_threads_do_not_overlap(self):
        results = OverlapCountingResults()
        data = SwigData(FakeElement(), results)
        errors = []

        def read():
            try:
                for _ in range(3):
                    data.get("deviceid")
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

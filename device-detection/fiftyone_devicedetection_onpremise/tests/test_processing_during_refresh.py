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
Flow Data is processed while the engine refreshes its data. A refresh on one
thread lets another thread go on processing, with every way of refreshing.
Also gives how many Flow Data were processed during the refreshes.
"""

import sys
import threading
import unittest
import warnings

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) "
             "AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114")

# The refreshes made on the refresh thread, so that it runs long enough for
# processing to be seen alongside it.
REFRESHES = 5

# Longer than the refreshes take, so the interpreter never makes the refresh
# thread give up the global interpreter lock. Flow Data can then only be
# processed during a refresh that gives the lock up itself.
SWITCH_INTERVAL_SECONDS = 600

# The pause after each Flow Data, which lets the refresh thread take the lock
# back when a refresh returns.
PAUSE_SECONDS = 0.001


class ProcessingDuringRefreshTests(unittest.TestCase):

    def setUp(self):
        self.element = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            performance_profile="MaxPerformance")
        self.pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}).add(self.element).build()
        self.addCleanup(self.pipeline.close)

    def processed_during(self, refresh, name):
        """The Flow Data processed from start to finish on this thread while
        another thread refreshed the engine REFRESHES times."""
        errors = []
        finished = threading.Event()

        def refresh_repeatedly():
            try:
                for _ in range(REFRESHES):
                    refresh()
            except Exception as e:
                errors.append(e)
            finally:
                finished.set()

        refresher = threading.Thread(target=refresh_repeatedly)
        interval = sys.getswitchinterval()
        sys.setswitchinterval(SWITCH_INTERVAL_SECONDS)
        try:
            refresher.start()
            processed = 0
            while not finished.is_set():
                with self.pipeline.create_flowdata() as flowdata:
                    flowdata.evidence.add("header.user-agent", mobile_ua)
                    flowdata.process()
                if not finished.is_set():
                    processed += 1
                finished.wait(PAUSE_SECONDS)
            refresher.join()
        finally:
            sys.setswitchinterval(interval)
        self.assertEqual([], errors)
        warnings.warn(
            f"{processed} Flow Data processed during {REFRESHES} refreshes "
            f"{name}")
        return processed

    def test_processing_goes_on_during_a_refresh(self):
        engine = self.element.engine
        self.assertGreater(self.processed_during(
            engine.refreshData, "from the data file in use"), 0)

    def test_processing_goes_on_during_a_refresh_from_a_file(self):
        engine = self.element.engine
        self.assertGreater(self.processed_during(
            lambda: engine.refreshDataFromFile(data_file), "from a file"), 0)

    def test_processing_goes_on_during_a_refresh_from_memory(self):
        engine = self.element.engine
        with open(data_file, "rb") as file:
            data = file.read()
        self.assertGreater(self.processed_during(
            lambda: engine.refreshDataFromMemory(data), "from memory"), 0)


if __name__ == "__main__":
    unittest.main()

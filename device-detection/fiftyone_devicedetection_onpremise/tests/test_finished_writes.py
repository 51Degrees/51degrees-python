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
Every FlowElement this package defines is processed, then a write to its
ElementData is expected to fail, as the thread safety page of the
specification requires. Reading values from the results is not a write.
"""

import importlib
import inspect
import pkgutil
import unittest

import fiftyone_devicedetection_onpremise
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

DATA_FILE = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
USER_AGENT = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
FINISHED = "finished processing"


def defined_flow_elements(package):
    """Every FlowElement class defined in the package's own modules."""
    found = set()
    for module in pkgutil.walk_packages(package.__path__,
                                        package.__name__ + "."):
        loaded = importlib.import_module(module.name)
        for _, cls in inspect.getmembers(loaded, inspect.isclass):
            if (issubclass(cls, FlowElement)
                    and cls.__module__.startswith(package.__name__)):
                found.add(cls)
    return found


class FinishedWritesTests(unittest.TestCase):

    def test_every_flow_element_refuses_writes_once_finished(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=DATA_FILE, licence_keys="", auto_update=False)
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", USER_AGENT)
            flowdata.process()
            data = flowdata.get("device")
            self.assertTrue(data.ismobile.value())
            with self.assertRaises(Exception) as caught:
                data.ismobile = False
            self.assertIn(FINISHED, str(caught.exception))
            self.assertTrue(data.ismobile.value())
        self.assertEqual(
            {DeviceDetectionOnPremise},
            defined_flow_elements(fiftyone_devicedetection_onpremise))


if __name__ == "__main__":
    unittest.main()

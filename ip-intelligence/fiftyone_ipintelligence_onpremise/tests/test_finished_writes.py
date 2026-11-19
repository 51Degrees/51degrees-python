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

import fiftyone_ipintelligence_onpremise
from fiftyone_ipintelligence_onpremise.constants import RESULTS_CLOSED
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import \
    IpIntelligenceOnPremise
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .constants import TestConstants

DATA_FILE = TestConstants.get_data_file_path()
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
        engine = IpIntelligenceOnPremise(
            data_file_path=DATA_FILE, licence_keys="", auto_update=False)
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("query.client-ip", "185.28.167.77")
            flowdata.process()
            data = flowdata.get("ip")
            name = data.get("registeredname")
            with self.assertRaises(Exception) as caught:
                data.registeredname = "written after processing"
            self.assertIn(FINISHED, str(caught.exception))
            self.assertEqual(name.value(), data.get("registeredname").value())
        self.assertEqual(
            {IpIntelligenceOnPremise},
            defined_flow_elements(fiftyone_ipintelligence_onpremise))

    def test_the_data_can_be_closed_once_finished(self):
        # Closing releases the native results, which is not a write, so it
        # works on finished data, as closing the FlowData does.
        engine = IpIntelligenceOnPremise(
            data_file_path=DATA_FILE, licence_keys="", auto_update=False)
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("query.client-ip", "185.28.167.77")
            flowdata.process()
            data = flowdata.get("ip")
            data.close()
            with self.assertRaises(Exception) as caught:
                data.get("registeredname")
            self.assertEqual(RESULTS_CLOSED, str(caught.exception))
            with self.assertRaises(Exception) as caught:
                data.registeredname = "written after processing"
            self.assertIn(FINISHED, str(caught.exception))


if __name__ == "__main__":
    unittest.main()

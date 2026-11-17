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
Every FlowElement this package defines, and every one its examples define, is
processed, then a write to its ElementData is expected to fail, as the thread
safety page of the specification requires.
"""

import importlib
import importlib.util
import inspect
import json
import os
import pkgutil

import fiftyone_pipeline_cloudrequestengine
from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

FINISHED = "finished processing"
EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples", "src", "fiftyone_pipeline_examples", "cloud")


class StandInRequestEngine(FlowElement):
    """Stands in for a Cloud Request Engine whose answer has an empty
    section for each of the given data keys."""

    def __init__(self, keys):
        super(StandInRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.flow_element_properties = {key: {} for key in keys}
        self.answer = json.dumps({key: {} for key in keys})

    def process_internal(self, flowdata):
        flowdata.set_element_data(
            ElementDataDictionary(self, {"cloud": self.answer}))


def load_example(name):
    """An example module, loaded from its file under its own name."""
    spec = importlib.util.spec_from_file_location(
        "example_" + name, os.path.join(EXAMPLES, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


class FinishedWritesTests(CloudRequestEngineTestsBase):

    def assert_writes_fail(self, flowdata, key):
        data = flowdata.get(key)
        with self.assertRaises(Exception) as caught:
            data.written_after_processing = True
        self.assertIn(FINISHED, str(caught.exception))

    def test_every_flow_element_refuses_writes_once_finished(self):
        cloud = CloudRequestEngine({
            "license_key": "a-licence-key",
            "requested_properties": ["device.ismobile"],
            "http_client": self.mock_http(),
        })
        engine = CloudEngine()
        engine.datakey = "device"
        flowdata = PipelineBuilder().add(cloud).add(engine).build() \
            .create_flowdata()
        flowdata.evidence.add("query.User-Agent", "iPhone")
        flowdata.process()
        self.assert_writes_fail(flowdata, "cloud")
        self.assert_writes_fail(flowdata, "device")
        self.assertEqual(
            {CloudEngine, CloudRequestEngine},
            defined_flow_elements(fiftyone_pipeline_cloudrequestengine))

    def test_every_example_flow_element_refuses_writes_once_finished(self):
        engines = load_example("engines")
        simple = load_example("simple_cloud_engine")
        elements = [engines.DeviceDetectionCloud(),
                    engines.IpIntelligenceCloud(),
                    engines.CountriesTranslationCloud(),
                    simple.SimpleCloudEngine()]
        for element in elements:
            builder = PipelineBuilder({"add_javascript_builder": False,
                                       "use_setheader_properties": False})
            flowdata = builder \
                .add(StandInRequestEngine([element.datakey])) \
                .add(element).build().create_flowdata()
            flowdata.process()
            self.assert_writes_fail(flowdata, element.datakey)


if __name__ == "__main__":
    import unittest
    unittest.main()

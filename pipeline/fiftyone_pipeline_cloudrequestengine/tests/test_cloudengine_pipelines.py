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
A cloud engine takes its properties from the Cloud Request Engine of its
pipeline. One cloud engine may be in several pipelines that share one Cloud
Request Engine, where its state is the same in each. A pipeline with
another Cloud Request Engine is refused, as multi-pipeline-elements.md
allows for an element this small, rather than the engine keeping its
properties for each pipeline.
"""

import json
import unittest

from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine

ANOTHER_REQUEST_ENGINE = (
    "This cloud engine is already in a pipeline with another Cloud Request "
    "Engine. Its properties come from that Cloud Request Engine, so a "
    "pipeline with a different one is refused. Build another cloud engine "
    "for this pipeline, or use the same Cloud Request Engine in both.")

MOBILE = {"ismobile": {"name": "IsMobile", "type": "Boolean"}}
VENDOR = {"hardwarevendor": {"name": "HardwareVendor", "type": "String"}}


class FakeCloudRequestEngine(FlowElement):
    """Stands in for a Cloud Request Engine whose key carries the given
    device properties."""

    def __init__(self, properties, answer):
        super(FakeCloudRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.flow_element_properties = {"device": properties}
        self.answer = answer

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"cloud": json.dumps({"device": self.answer})}))


def device_engine():
    engine = CloudEngine()
    engine.datakey = "device"
    return engine


def device_value(pipeline, name):
    with pipeline.create_flowdata() as flowdata:
        flowdata.process()
        return flowdata.get("device").get(name).value()


class CloudEnginePipelinesTests(unittest.TestCase):

    def test_a_pipeline_with_another_request_engine_is_refused(self):
        engine = device_engine()
        first = Pipeline([
            FakeCloudRequestEngine(MOBILE, {"ismobile": True}), engine])

        with self.assertRaises(Exception) as raised:
            Pipeline([FakeCloudRequestEngine(
                VENDOR, {"hardwarevendor": "Apple"}), engine])

        self.assertEqual(ANOTHER_REQUEST_ENGINE, str(raised.exception))
        self.assertEqual([first], engine.pipelines)
        self.assertEqual(["ismobile"], list(engine.get_properties()))
        self.assertIs(True, device_value(first, "ismobile"))

    def test_pipelines_sharing_a_request_engine_share_the_engine(self):
        request_engine = FakeCloudRequestEngine(MOBILE, {"ismobile": True})
        engine = device_engine()
        first = Pipeline([request_engine, engine])
        second = Pipeline([request_engine, engine])

        self.assertEqual([first, second], engine.pipelines)
        self.assertEqual(["ismobile"], list(engine.get_properties()))
        for pipeline in (first, second):
            self.assertIs(True, device_value(pipeline, "ismobile"))


if __name__ == "__main__":
    unittest.main()


"""
The JSON Builder writes the key of each top-level entry and of each sub-entry,
including the meta-Property suffixes, in lower case, apart from
javascriptProperties, as the JSON Builder specification says.
"""

import unittest

from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class MixedCaseElement(FlowElement):

    def __init__(self):
        super(MixedCaseElement, self).__init__()
        self.datakey = "MixedCase"
        self.properties = {
            "DelayedProp": {
                "name": "DelayedProp", "type": "string",
                "delayexecution": True},
            "OtherProp": {
                "name": "OtherProp", "type": "string",
                "evidenceproperties": ["delayedprop"]},
            "EmptyProp": {"name": "EmptyProp", "type": "string"}}

    def process_internal(self, flowdata):
        # FlowData.get reads the data under the lower case key.
        flowdata.data["mixedcase"] = ElementDataDictionary(
            self, {"DelayedProp": "a", "OtherProp": "b", "EmptyProp": None})


class JsonBuilderLowerCaseTests(unittest.TestCase):

    def process(self):
        pipeline = PipelineBuilder({}).add(MixedCaseElement()).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        return flowdata.jsonbundler.json

    def test_every_key_is_lower_case_but_javascript_properties(self):
        json = self.process()
        self.assertIn("javascriptProperties", json)
        self.assertIn("mixedcase", json)
        for key, value in json.items():
            if key == "javascriptProperties":
                continue
            self.assertEqual(key.lower(), key)
            for sub_key in value:
                self.assertEqual(sub_key.lower(), sub_key, sub_key)

    def test_the_meta_property_keys_are_lower_case(self):
        section = self.process()["mixedcase"]
        self.assertTrue(section["delayedpropdelayexecution"])
        self.assertIn("otherpropevidenceproperties", section)
        self.assertIn("emptypropnullreason", section)
        self.assertIsNone(section["emptyprop"])


if __name__ == "__main__":
    unittest.main()

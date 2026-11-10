
"""
A Property whose value is a list of Element Data is written as a list of
objects, each following the null rules of the JSON Builder specification, and
the other Properties are written beside it.
"""

import unittest

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class ProfilesElement(FlowElement):

    def __init__(self):
        super(ProfilesElement, self).__init__()
        self.datakey = "hardware"
        self.properties = {
            "profiles": {"name": "Profiles", "type": "array"},
            "vendor": {"name": "Vendor", "type": "string"},
            "model": {"name": "Model", "type": "string"},
            "colour": {"name": "Colour", "type": "string"},
            "script": {"name": "Script", "type": "javascript"},
            "size": {"name": "Size", "type": "string"}}

    def process_internal(self, flowdata):
        records = [
            {"hardwarename": AspectPropertyValue(value="Phone"),
             "hardwarevendor": AspectPropertyValue(no_value_message="No data"),
             "hardwaremodel": None},
            {"hardwarename": AspectPropertyValue(value="Tablet")},
            {"hardwarename": AspectPropertyValue()}]
        flowdata.set_element_data(ElementDataDictionary(
            self, {"profiles": records,
                   "vendor": AspectPropertyValue(value="Acme"),
                   "model": None,
                   "colour": AspectPropertyValue(
                       no_value_message="No colour"),
                   "script": None,
                   "size": AspectPropertyValue()}))


class JsonBuilderRecordTests(unittest.TestCase):

    def process_json(self):
        pipeline = PipelineBuilder({}).add(ProfilesElement()).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        return flowdata.jsonbundler.json

    def process(self):
        return self.process_json()["hardware"]

    def test_each_record_is_an_object(self):
        self.assertEqual(
            [{"hardwarename": "Phone",
              "hardwarevendor": None,
              "hardwarevendornullreason": "No data"},
             {"hardwarename": "Tablet"},
             {"hardwarename": None, "hardwarenamenullreason": "Unknown"}],
            self.process()["profiles"])

    def test_a_null_that_was_not_assigned_no_value_has_no_entry(self):
        self.assertNotIn("hardwaremodel", self.process()["profiles"][0])

    def test_the_other_properties_are_still_written(self):
        self.assertEqual("Acme", self.process()["vendor"])

    def test_a_top_level_null_not_assigned_no_value_has_no_entry(self):
        hardware = self.process()
        self.assertNotIn("model", hardware)
        self.assertNotIn("modelnullreason", hardware)

    def test_a_null_javascript_property_is_still_listed(self):
        json = self.process_json()
        self.assertNotIn("script", json["hardware"])
        self.assertIn("hardware.script", json["javascriptProperties"])

    def test_no_value_with_no_message_has_a_text_reason(self):
        hardware = self.process()
        self.assertIsNone(hardware["size"])
        self.assertEqual("Unknown", hardware["sizenullreason"])

    def test_a_top_level_property_assigned_no_value_is_null(self):
        hardware = self.process()
        self.assertIsNone(hardware["colour"])
        self.assertEqual("No colour", hardware["colournullreason"])


if __name__ == "__main__":
    unittest.main()

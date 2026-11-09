
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
            "vendor": {"name": "Vendor", "type": "string"}}

    def process_internal(self, flowdata):
        records = [
            {"hardwarename": AspectPropertyValue(value="Phone"),
             "hardwarevendor": AspectPropertyValue(no_value_message="No data"),
             "hardwaremodel": None},
            {"hardwarename": AspectPropertyValue(value="Tablet")}]
        flowdata.set_element_data(ElementDataDictionary(
            self, {"profiles": records,
                   "vendor": AspectPropertyValue(value="Acme")}))


class JsonBuilderRecordTests(unittest.TestCase):

    def process(self):
        pipeline = PipelineBuilder({}).add(ProfilesElement()).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        return flowdata.jsonbundler.json["hardware"]

    def test_each_record_is_an_object(self):
        self.assertEqual(
            [{"hardwarename": "Phone",
              "hardwarevendor": None,
              "hardwarevendornullreason": "No data"},
             {"hardwarename": "Tablet"}],
            self.process()["profiles"])

    def test_a_null_that_was_not_assigned_no_value_has_no_entry(self):
        self.assertNotIn("hardwaremodel", self.process()["profiles"][0])

    def test_the_other_properties_are_still_written(self):
        self.assertEqual("Acme", self.process()["vendor"])


if __name__ == "__main__":
    unittest.main()

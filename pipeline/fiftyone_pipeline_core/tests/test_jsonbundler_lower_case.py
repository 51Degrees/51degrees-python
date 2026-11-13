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
The JSON Builder writes the key of each top-level entry and of each sub-entry,
including the meta-Property suffixes, in lower case, apart from
javascriptProperties, as the JSON Builder specification says.
"""

import unittest

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
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
        # Set as a real element sets it, under its mixed case data key.
        flowdata.set_element_data(ElementDataDictionary(
            self, {"DelayedProp": "a", "OtherProp": "b",
                   "EmptyProp": AspectPropertyValue(
                       no_value_message="No value")}))


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
        self.assertEqual("No value", section["emptypropnullreason"])
        self.assertIsNone(section["emptyprop"])
        self.assertEqual("a", section["delayedprop"])
        self.assertEqual("b", section["otherprop"])


if __name__ == "__main__":
    unittest.main()

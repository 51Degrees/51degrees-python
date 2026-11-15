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

"""The JSON Builder writes delayexecution only for a Property that has a
value, as the JSON Builder specification's meta-Property table says.

The delayed execution information comes from each element's property
metadata, which an element can lack for a while after the pipeline is
built, for example while that metadata is still being fetched. The JSON
Builder reads the information again while the element has no properties,
and keeps it once the element has them."""

import unittest

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


def delayed(name):
    return {"name": name, "type": "javascript", "delayexecution": True}


class DelayedElement(FlowElement):

    def __init__(self):
        super(DelayedElement, self).__init__()
        self.datakey = "delayed"
        self.properties = {
            "withvalue": delayed("WithValue"),
            "novalue": delayed("NoValue"),
            "plainnull": delayed("PlainNull")}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {
            "withvalue": AspectPropertyValue(value="script"),
            "novalue": AspectPropertyValue(no_value_message="No script"),
            "plainnull": None}))


# The property metadata of DiscoveringElement once it is known. Value can
# be found once the delayed JavaScript property has run.
KNOWN_PROPERTIES = {
    "javascript": delayed("JavaScript"),
    "value": {
        "name": "Value",
        "type": "string",
        "evidenceproperties": ["javascript"]}}


class DiscoveringElement(FlowElement):
    """
    An element with no properties until discover is called, as an element
    whose property metadata could not be fetched when the pipeline was built
    has none until a later fetch succeeds.
    """

    def __init__(self):
        super(DiscoveringElement, self).__init__()
        self.datakey = "discovering"
        self.properties = {}

    def discover(self):
        self.properties = dict(KNOWN_PROPERTIES)

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {
            "javascript": AspectPropertyValue(value="script"),
            "value": AspectPropertyValue(
                no_value_message="Needs the JavaScript to run")}))


def process(pipeline):
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    return flowdata.jsonbundler.json["discovering"]


class JsonBuilderDelayExecutionTests(unittest.TestCase):

    def test_delayexecution_is_written_only_for_a_property_with_a_value(self):
        pipeline = PipelineBuilder({}).add(DelayedElement()).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        section = flowdata.jsonbundler.json["delayed"]
        self.assertTrue(section["withvaluedelayexecution"])
        self.assertNotIn("novaluedelayexecution", section)
        self.assertNotIn("plainnulldelayexecution", section)

    def test_information_is_read_once_the_properties_are_known(self):
        element = DiscoveringElement()
        pipeline = PipelineBuilder({}).add(element).build()
        self.addCleanup(pipeline.close)

        # Requests processed before the element's properties are known
        # have nothing for the element.
        self.assertEqual({}, process(pipeline))
        self.assertEqual({}, process(pipeline))

        # A later request has the delayed execution information.
        element.discover()
        section = process(pipeline)
        self.assertIs(True, section.get("javascriptdelayexecution"), section)
        self.assertEqual(
            ["discovering.javascript"],
            section.get("valueevidenceproperties"),
            section)

    def test_information_is_kept_once_it_is_known(self):
        element = DiscoveringElement()
        element.discover()
        pipeline = PipelineBuilder({}).add(element).build()
        self.addCleanup(pipeline.close)

        section = process(pipeline)
        self.assertIs(True, section.get("javascriptdelayexecution"), section)

        # Metadata with no delayed execution flags, so the next request
        # shows whether the information was read again.
        element.properties = {
            name: {
                key: value for key, value in meta.items()
                if key not in ("delayexecution", "evidenceproperties")}
            for name, meta in KNOWN_PROPERTIES.items()}

        section = process(pipeline)
        self.assertIs(True, section.get("javascriptdelayexecution"), section)
        self.assertEqual(
            ["discovering.javascript"],
            section.get("valueevidenceproperties"),
            section)


if __name__ == "__main__":
    unittest.main()

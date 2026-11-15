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

"""One JSON Builder in two Pipelines whose elements share a data key. The
delayed execution information of each Pipeline comes from its own
element, as multi-pipeline-elements.md asks of an element that keeps state
for a Pipeline."""

import unittest

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.jsonbundler import JSONBundlerElement
from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_core.sequenceelement import SequenceElement


class DeviceElement(FlowElement):
    """An element under the data key device whose JavaScript property runs
    later or not, as its property metadata says."""

    def __init__(self, delayed):
        super(DeviceElement, self).__init__()
        self.datakey = "device"
        self.properties = {
            "javascript": {
                "name": "JavaScript", "type": "javascript",
                "delayexecution": delayed},
            "value": {
                "name": "Value", "type": "string",
                "evidenceproperties": ["javascript"]}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {
            "javascript": AspectPropertyValue(value="script"),
            "value": AspectPropertyValue(value="value")}))


def device_section(pipeline):
    with pipeline.create_flowdata() as flowdata:
        flowdata.process()
        return flowdata.jsonbundler.json["device"]


class JsonBuilderPipelinesTests(unittest.TestCase):

    def test_each_pipeline_has_the_information_of_its_own_element(self):
        json_builder = JSONBundlerElement()
        delayed = Pipeline(
            [SequenceElement(), DeviceElement(True), json_builder])
        not_delayed = Pipeline(
            [SequenceElement(), DeviceElement(False), json_builder])

        for _ in range(2):
            section = device_section(delayed)
            self.assertIs(
                True, section.get("javascriptdelayexecution"), section)
            self.assertEqual(
                ["device.javascript"],
                section.get("valueevidenceproperties"), section)

            section = device_section(not_delayed)
            self.assertNotIn("javascriptdelayexecution", section)
            self.assertNotIn("valueevidenceproperties", section)


if __name__ == "__main__":
    unittest.main()

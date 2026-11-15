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
The reason a Cloud Aspect Engine gives for a missing property, decided in
the order the properties specification sets out, with the message of the
missing properties table for that reason.
"""

import json
import unittest

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# The configurator the Resource Key rows link to, with this repository's
# campaign parameters.
CONFIGURATOR = (
    "https://configure.51degrees.com/?utm_source=code&utm_medium=comment"
    "&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-"
    "src-fiftyone_pipeline_engines-missingproperty_service.py"
    "&utm_term=missing-property-configurator")


class FakeCloudRequestEngine(FlowElement):
    """Stands in for the Cloud Request Engine of a key that carries only the
    device product, with two of its properties."""

    def __init__(self):
        super(FakeCloudRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.flow_element_properties = {"device": {
            "ismobile": {"name": "IsMobile", "type": "Boolean"},
            "hardwarevendor": {"name": "HardwareVendor", "type": "String"}}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"cloud": json.dumps({"device": {"ismobile": True}})}))


class UndiscoveredCloudRequestEngine(FakeCloudRequestEngine):
    """Stands in for a Cloud Request Engine whose request for the property
    list failed when it was built, so its properties are not known."""

    def known_flow_element_properties(self):
        return None


def build(request_engine, datakey, restricted=None):
    engine = CloudEngine()
    engine.datakey = datakey
    if restricted is not None:
        engine.set_restricted_properties(restricted)
    pipeline = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False}).add(
            request_engine).add(engine).build()
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    return pipeline, flowdata


class CloudReasonTests(unittest.TestCase):

    def message(self, request_engine, datakey, name, restricted=None):
        pipeline, flowdata = build(request_engine, datakey, restricted)
        self.addCleanup(pipeline.close)
        with self.assertRaises(Exception) as raised:
            flowdata.get(datakey).get(name)
        return str(raised.exception)

    def test_a_product_the_key_does_not_include(self):
        self.assertEqual(
            "Property 'country' not found in data for element 'location'. "
            "This is because your resource key does not include access to "
            "any properties under 'location'. Check or create a resource key "
            "with the properties you need in the configurator at "
            + CONFIGURATOR + ".",
            self.message(FakeCloudRequestEngine(), "location", "country"))

    def test_a_property_the_key_does_not_include(self):
        self.assertEqual(
            "Property 'browsername' not found in data for element 'device'. "
            "This is because your resource key does not include access to "
            "this property. The properties included for your key under "
            "'device' are IsMobile,HardwareVendor. Check or change your key "
            "in the configurator at " + CONFIGURATOR + ".",
            self.message(FakeCloudRequestEngine(), "device", "browsername"))

    def test_a_listed_property_not_in_the_answer_was_excluded(self):
        self.assertEqual(
            "Property 'HardwareVendor' not found in data for element "
            "'device'. This is because the property has been excluded when "
            "configuring the engine.",
            self.message(
                FakeCloudRequestEngine(), "device", "HardwareVendor"))

    def test_a_property_left_out_of_the_restricted_list_was_excluded(self):
        self.assertIn(
            "This is because the property has been excluded when "
            "configuring the engine.",
            self.message(
                FakeCloudRequestEngine(), "device", "hardwarevendor",
                restricted=["IsMobile"]))

    def test_a_failed_request_for_the_property_list(self):
        self.assertEqual(
            "Property 'browsername' not found in data for element 'device'. "
            "This is because an upstream cloud request failed, so no data "
            "was available to populate the property.",
            self.message(
                UndiscoveredCloudRequestEngine(), "device", "browsername"))


if __name__ == "__main__":
    unittest.main()

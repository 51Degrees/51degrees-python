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

import os
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import DeviceDetectionOnPremise
from fiftyone_devicedetection_shared.utils import *
from fiftyone_devicedetection_onpremise import constants

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
            "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
            "/11D167 Safari/9537.53")

# The match metric properties as the on-premise device detection
# specification's table gives them, in the table's order. A list of strings
# has the type name the native code gives one, "string[]".
MATCH_METRICS = [
    ("MatchedNodes", "int",
     "Indicates the number of hash nodes matched within the Evidence."),
    ("Difference", "int",
     "Used when detection method is not Exact or None. The larger the "
     "value the less confident the detector is in this result."),
    ("Drift", "int",
     "The drift of every component's result added together, each "
     "result's drift being how far, in character positions, the "
     "substring's hashes were found from where they were expected. Never "
     "the largest or smallest result alone."),
    ("DeviceId", "string",
     "Contains the profile ids of the matching profiles, separated by a "
     "hyphen symbol. For example "
     "[HardwareId]-[PlatformId]-[BrowserId]-[CrawlerId]. By convention, "
     "these will be in component Id order. There will often be 4 ids "
     "present, but this is not guaranteed."),
    ("UserAgents", "string[]",
     "The User-Agent values that were matched, each listed once across "
     "every result. Populated when the Update Matched User Agent "
     "configuration option is on, which it is by default."),
    ("Iterations", "int",
     "The number of iterations carried out in order to find a match. This "
     "is the number of nodes in the graph which have been visited."),
    ("Method", "string", "The method used to determine the match result.")]

# Create a simple pipeline to access the engine with and process it with flow data
deviceDetectionOnPremiseEngine = DeviceDetectionOnPremise(
            data_file_path = data_file, 
            licence_keys = "",
            auto_update=False)
pipeline = PipelineBuilder() \
            .add(deviceDetectionOnPremiseEngine) \
            .build()

# Releases the native engine once every test in the module has run.
def tearDownModule():
    pipeline.close()

class PropertyTests(unittest.TestCase):
    def test_available_properties(self):

        """!
        Tests whether the all the properties present in the engine when initialised with a resource key are accessible.
        """

        flowData = pipeline.create_flowdata()
        self.addCleanup(flowData.close)
        flowData.evidence.add("header.user-agent", mobile_ua)
        flowData.process()
        device = flowData.device

        # Get list of all the properties in the engine
        properties_list = deviceDetectionOnPremiseEngine.get_properties()

        # Run test checks on all the properties available in data file
        for propertykey, propertymeta in properties_list.items():
            property = propertymeta["name"]
            dd_property_value = device[property]
            self.assertIsNotNone("Property: " + property +" is not present in the results.", dd_property_value)
            if(dd_property_value.has_value()):
                self.assertNotEqual(property + ".value should not be null", dd_property_value.value(), "noValue")
                self.assertIsNotNone(property + ".value should not be null", dd_property_value.value())
            else:
                self.assertIsNotNone(property + ".noValueMessage should not be null", dd_property_value.no_value_message())

    def test_match_metrics_description(self):

        """!
        Tests whether the descriptions of all match metric properties are returned correctly.
        """

        flowData = pipeline.create_flowdata()
        self.addCleanup(flowData.close)
        flowData.evidence.add("header.user-agent", mobile_ua)
        flowData.process()

        # Get list of all the properties in the engine
        properties_list = deviceDetectionOnPremiseEngine.get_properties()

        self.assertEqual(
            properties_list['deviceid']['description'], constants.DEVICE_ID_DESCRIPTION,
            properties_list['deviceid']['name'] + '.description does not match "' + constants.DEVICE_ID_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['useragents']['description'], constants.USER_AGENTS_DESCRIPTION,
            properties_list['useragents']['name'] + '.description does not match "' + constants.USER_AGENTS_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['difference']['description'], constants.DIFFERENCE_DESCRIPTION,
            properties_list['difference']['name'] + '.description does not match "' + constants.DIFFERENCE_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['drift']['description'], constants.DRIFT_DESCRIPTION,
            properties_list['drift']['name'] + '.description does not match "' + constants.DRIFT_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['matchednodes']['description'], constants.MATCHED_NODES_DESCRIPTION,
            properties_list['matchednodes']['name'] + '.description does not match "' + constants.MATCHED_NODES_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['iterations']['description'], constants.ITERATIONS_DESCRIPTION,
            properties_list['iterations']['name'] + '.description does not match "' + constants.ITERATIONS_DESCRIPTION + '"')
        self.assertEqual(
            properties_list['method']['description'], constants.METHOD_DESCRIPTION,
            properties_list['method']['name'] + '.description does not match "' + constants.METHOD_DESCRIPTION + '"')

    def test_match_metrics_metadata(self):

        """!
        Tests that each match metric property has the metadata the
        specification gives it, with the "Device Metrics" category, the
        "Metrics" component and every data file.
        """

        properties_list = deviceDetectionOnPremiseEngine.get_properties()

        for name, value_type, description in MATCH_METRICS:
            self.assertEqual({
                "name": name,
                "type": value_type,
                "datafiles": ["Lite", "Premium", "Enterprise", "TAC"],
                "category": "Device Metrics",
                "description": description,
                "component": "Metrics"},
                properties_list[name.lower()])

    def test_match_metrics_follow_the_data_file_properties(self):

        """!
        Tests that the match metric properties are listed after the
        properties from the data file, in the order of the specification's
        table.
        """

        keys = list(deviceDetectionOnPremiseEngine.get_properties())
        metrics = [name.lower() for name, _, _ in MATCH_METRICS]

        self.assertEqual(metrics, keys[-len(metrics):])

    def test_value_types(self):

        """!
        Tests value types of the properties present present in the engine 
        """

        flowData = pipeline.create_flowdata()
        self.addCleanup(flowData.close)
        flowData.evidence.add("header.user-agent", mobile_ua)
        flowData.process()
        device = flowData.device

        # Get list of all the properties in the engine
        properties_list = deviceDetectionOnPremiseEngine.get_properties()

        # Run test check valuetypes of properties
        for propertykey, propertymeta in properties_list.items():
            # Engine properties
            property = propertymeta["name"]
            expected_type = propertymeta["type"]

            # Flowdata properties
            dd_property_value = device[property]
            if property.lower() == 'javascriptgethighentropyvalues':
                self.assertFalse(dd_property_value.has_value())
                continue
            value = dd_property_value.value()
            self.assertIsNotNone("Property: " + property +" is not present in the results.", dd_property_value)
            self.assertTrue("Expected type for " + property + " is " + expected_type + 
            " but actual type is " + get_value_type(value), is_same_type(value, expected_type))




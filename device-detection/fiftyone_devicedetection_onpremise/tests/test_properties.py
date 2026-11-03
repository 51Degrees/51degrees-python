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

data_file = "./src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
            "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
            "/11D167 Safari/9537.53")

# Create a simple pipeline to access the engine with and process it with flow data
deviceDetectionOnPremiseEngine = DeviceDetectionOnPremise(
            data_file_path = data_file, 
            licence_keys = "",
            auto_update=False)
pipeline = PipelineBuilder() \
            .add(deviceDetectionOnPremiseEngine) \
            .build()

class PropertyTests(unittest.TestCase):
    def test_available_properties(self):

        """!
        Tests whether the all the properties present in the engine when initialised with a resource key are accessible.
        """

        flowData = pipeline.create_flowdata()
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

    def test_value_types(self):

        """!
        Tests value types of the properties present present in the engine 
        """

        flowData = pipeline.create_flowdata()
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




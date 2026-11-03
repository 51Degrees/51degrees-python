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
from fiftyone_devicedetection_onpremise.swig_data import SwigData
from fiftyone_devicedetection_shared.utils import *

data_file = "./src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/51Degrees-LiteV4.1.hash"

# Create a simple pipeline to access the engine with and process it with flow data
deviceDetectionOnPremiseEngine = DeviceDetectionOnPremise(
            data_file_path = data_file, 
            licence_keys = "",
            auto_update=False)
pipeline = PipelineBuilder() \
            .add(deviceDetectionOnPremiseEngine) \
            .build()

class SwigTests(unittest.TestCase):

    # Mock the native code parts so we are only testing the wrapper.
    class MockSwigResults:
        class MockSwigValue:
            def __init__(self, value, noValueMessage):
                self.value = value
                self.noValueMessage = noValueMessage

            def hasValue(self):
                return True

            def getNoValueMessage(self):
                return self.noValueMessage

            def getValue(self):
                return self.value

        def __init__(self, values):
            self.values = values

        def getAvailableProperties(self):
            return self.values.len()

        def containsProperty(self, propertyName):
            return propertyName.lower() in self.values

        def getProperties(self):
            return self.values.keys()

        def getPropertyName(self, requiredPropertyIndex):
            return self.values.keys()[requiredPropertyIndex]
            
        def getValues(self, propertyName):
            return self.MockSwigValue(self.values[propertyName.lower()], "")

        def getValueAsString(self, propertyName):
            return self.MockSwigValue(self.values[propertyName.lower()], "")
            
        def getValueAsBool(self, propertyName):
            return self.MockSwigValue(self.values[propertyName.lower()], "")
            
        def getValueAsInteger(self, propertyName):
            return self.MockSwigValue(self.values[propertyName.lower()], "")
            
        def getValueAsDouble(self, propertyName):
            return self.MockSwigValue(self.values[propertyName.lower()], "")
            
    # Test fetching a value of a certain type through the wrapper/
    def run_type_tests(self, property, type, value):
        
        engine = pipeline.flow_elements_list["device"]

        # Keep hold of the existing properties to reset at the end.
        realProperties = engine.properties

        # Set up the properties in the engine.
        engine.properties = {
            property.lower(): {"name": property, "type": type, "datafiles": [engine.engine.getProduct()]}
        }

        # Create a new SwigData with the native results mocked.
        values = {property.lower(): value}
        device = SwigData(engine, self.MockSwigResults(values))

        # Check the values are returned and that they are correct
        self.assertIsNotNone(device[property.lower()].value())
        self.assertEqual(value, device[property.lower()].value())

        # Reset the properties in the enigne.
        engine.properties = realProperties

    def test_string(self):
        self.run_type_tests("StringValue", "string", "some string")
    def test_bool(self):
        self.run_type_tests("BoolValue", "bool", True)
    def test_int(self):
        self.run_type_tests("IntValue", "int", 51)
    def test_double(self):
        self.run_type_tests("DoubleValue", "double", 5.1)
    def test_list(self):
        self.run_type_tests("ListValue", "string[]", ["some string", "another string"])

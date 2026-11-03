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

from fiftyone_location.location_pipelinebuilder import LocationPipelineBuilder
from .test_helper import *

location_LAT = '51.4578261';
location_LON = '-0.975922996290084';

if "resource_key" in os.environ:
    resource_key = os.environ["resource_key"]
else:
    raise Exception("To run the cloud tests, please set a valid 51Degrees "
                    "cloud resource key as the resource_key environment variable.")

# Create a simple pipeline to access the engine with and process it with flow data
pipeline = LocationPipelineBuilder(resource_key = resource_key, location_provider =  "fiftyonedegrees").build()

location_engine = pipeline.get_element("location")
flowData = pipeline.create_flowdata();
flowData.evidence.add('query.51D_Pos_latitude', location_LAT);
flowData.evidence.add('query.51D_Pos_longitude', location_LON);
flowData.process()

class PropertyTests(unittest.TestCase):

    def test_available_properties_fiftyonedegrees(self):

        """!
        Tests value types of the properties present present in the engine
        """

        location = flowData.get(location_engine.datakey)

        # Get list of all the properties in the engine
        properties_list = location_engine.get_properties()
        for propertykey, propertymeta in properties_list.items():
            property = propertymeta["name"].lower()
            dd_property_value = location[property]
            self.assertIsNotNone("Property: " + property +" is not present in the results.", dd_property_value)
            if(dd_property_value.has_value()):
                self.assertNotEqual(property + ".value should not be null", dd_property_value.value(), "noValue")
                self.assertIsNotNone(property + ".value should not be null", dd_property_value.value())
            else:
                self.assertIsNotNone(property + ".noValueMessage should not be null", dd_property_value.no_value_message())

    def test_value_types_fiftyonedegrees(self):

        """!
        Tests whether the all the properties present in the engine when initialised with a resource key are accessible.
        """

        location = flowData.get(location_engine.datakey)

        # Get list of all the properties in the engine
        properties_list = location_engine.get_properties()

        # Run test check valuetypes of properties
        for propertykey, propertymeta in properties_list.items():
            # Engine properties
            property = propertymeta["name"].lower()
            expected_type = propertymeta["type"]

            # Flowdata properties
            dd_property_value = location[property]
            if dd_property_value.has_value():
                self.assertIsNotNone("Property: " + property +" is not present in the results.", dd_property_value)
                value = dd_property_value.value()
                self.assertTrue("Expected type for " + property + " is " + expected_type +
                " but actual type is " + get_value_type(value), is_same_type(value, expected_type))

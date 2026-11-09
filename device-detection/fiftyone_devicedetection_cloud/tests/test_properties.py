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

import pytest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine
from fiftyone_devicedetection_cloud.devicedetection_cloud import DeviceDetectionCloud
from fiftyone_devicedetection_shared.utils import (
    get_properties_from_header_file,
    get_value_type,
    is_same_type,
)

from .live_cloud import find_resource_key, no_resource_key

pytestmark = pytest.mark.live

header_file_path = "./tests/51Degrees.csv"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
            "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
            "/11D167 Safari/9537.53")

chrome_ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# TODO remove setheader properties from this list once UACH datafile is released.
exclude_properties = ["setheaderbrowseraccept-ch", "setheaderplatformaccept-ch", "setheaderhardwareaccept-ch"]

NO_KEY = no_resource_key(
    "the device product",
    "every device detection property listed in " + header_file_path,
    several=True)

class PropertyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.resource_key = find_resource_key()
        cls.pipeline = None
        if cls.resource_key and os.path.isfile(header_file_path):
            cls.properties_list = get_properties_from_header_file(
                header_file_path)
            cls.engine = DeviceDetectionCloud()
            cls.pipeline = PipelineBuilder() \
                .add(CloudRequestEngine({"resource_key": cls.resource_key})) \
                .add(cls.engine) \
                .build()

    def setUp(self):
        if not self.resource_key:
            self.fail(NO_KEY)
        if self.pipeline is None:
            # The property list comes from an asset the build fetches with
            # a licence key, so a run without it says which file is missing.
            self.skipTest(
                f"The property list file '{header_file_path}' is not "
                "present, so the property coverage tests cannot run. It is "
                "fetched by ci/fetch-assets.ps1 when a device detection "
                "licence key is available.")

    def test_available_properties(self):

        """!
        Tests whether the all the properties present in the engine when initialised with a resource key are accessible.
        """

        flowData = self.pipeline.create_flowdata()
        flowData.evidence.add("header.user-agent", mobile_ua)
        flowData.process()
        elementData = flowData.get(self.engine.datakey)

        # Get dictionary of elementdata properties
        dd_property_dict = elementData.as_dictionary()

        #RUn test checks on all the properties available in header file
        for property in self.properties_list:
            property = property.lower()
            if(property not in exclude_properties):
                if(property in dd_property_dict):
                    dd_property_value = dd_property_dict[property]
                    if(dd_property_value.has_value()):
                        self.assertNotEqual(property + ".value should not be null", dd_property_value.value(), "noValue")
                        self.assertIsNotNone(property + ".value should not be null", dd_property_value.value())
                    else:
                        self.assertIsNotNone(dd_property_value.no_value_message())
                else:
                    raise Exception("Property: " + property +" is not present in the results.")
            else:
                print("Property: " + property + " excluded from tests.\n");

    def test_value_types(self):

        """!
        Tests value types of the properties present present in the engine 
        """
        
        flowData = self.pipeline.create_flowdata()
        flowData.evidence.add("header.user-agent", chrome_ua)
        flowData.process()
        elementData = flowData.get(self.engine.datakey)

        # Get dictionary of elementdata properties
        dd_property_dict = elementData.as_dictionary()
        
        # Get properties from the engine
        properties_list = self.engine.get_properties()

        # Run test check valuetypes of properties
        for propertykey, propertymeta in properties_list.items():
            # Engine properties
            property = propertymeta["name"].lower()
            expected_type = propertymeta["type"]
            if(property in dd_property_dict and property not in exclude_properties):
                dd_property_value = dd_property_dict[property]

                self.assertIsNotNone(dd_property_value, "Property: " + property + " is not present in the results.")
                if dd_property_value.has_value():
                    value = dd_property_value.value()
                    self.assertTrue(is_same_type(value, expected_type),
                                    "Expected type for " + property + " is " + expected_type +
                                    " but actual type is " + get_value_type(value))
                else:
                    self.assertIsNotNone(dd_property_value.no_value_message())

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
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine
from fiftyone_devicedetection_cloud.devicedetection_cloud import DeviceDetectionCloud
from fiftyone_devicedetection_shared.utils import (
    get_properties_from_header_file,
    get_value_type,
    is_same_type,
)

header_file_path = "./tests/51Degrees.csv"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
            "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
            "/11D167 Safari/9537.53")

chrome_ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# TODO remove setheader properties from this list once UACH datafile is released.
exclude_properties = ["setheaderbrowseraccept-ch", "setheaderplatformaccept-ch", "setheaderhardwareaccept-ch"]

# Resource key environment variables follow the 51Degrees convention, which
# is that every one of them starts with "_51DEGREES_RESOURCE_KEY". The name
# used before the convention was adopted is still read, so an existing setup
# keeps working.
RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"
LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"

resource_key = (os.environ.get(RESOURCE_KEY_ENV_VAR)
                or os.environ.get(LEGACY_RESOURCE_KEY_ENV_VAR))

if not resource_key:
    # Skipping rather than raising, so a run without a key shows as skipped
    # and names the variable, instead of turning into a collection error.
    import pytest

    pytest.skip(
        "No resource key found, so the tests that call the cloud service "
        f"cannot run. Set the environment variable '{RESOURCE_KEY_ENV_VAR}' "
        f"(the older name '{LEGACY_RESOURCE_KEY_ENV_VAR}' is still read). "
        "Create a resource key for free at "
        "https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-tests-test_properties.py&utm_term=resource-key-required",
        allow_module_level=True)

if not os.path.isfile(header_file_path):
    # The property list comes from an asset the build fetches with a licence
    # key. Without it these tests cannot run, so skip rather than turn a
    # missing asset into a failure.
    import pytest

    pytest.skip(
        f"The property list file '{header_file_path}' is not present, so "
        "the property coverage tests cannot run. It is fetched by "
        "ci/fetch-assets.ps1 when a device detection licence key is "
        "available.",
        allow_module_level=True)

# Get Properties list
properties_list = get_properties_from_header_file(header_file_path)

# Create a simple pipeline to access the engine with and process it with flow data
cloudRequestEngine = CloudRequestEngine({"resource_key": resource_key})
deviceDetectionCloudEngine = DeviceDetectionCloud()
pipeline = PipelineBuilder() \
        .add(cloudRequestEngine) \
        .add(deviceDetectionCloudEngine) \
        .build()
            
class PropertyTests(unittest.TestCase):

    def test_available_properties(self):

        """!
        Tests whether the all the properties present in the engine when initialised with a resource key are accessible.
        """

        flowData = pipeline.create_flowdata()
        flowData.evidence.add("header.user-agent", mobile_ua)
        flowData.process()
        elementData = flowData.get(deviceDetectionCloudEngine.datakey)

        # Get dictionary of elementdata properties
        dd_property_dict = elementData.as_dictionary()

        #RUn test checks on all the properties available in header file
        for property in properties_list:
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
        
        flowData = pipeline.create_flowdata()
        flowData.evidence.add("header.user-agent", chrome_ua)
        flowData.process()
        elementData = flowData.get(deviceDetectionCloudEngine.datakey)

        # Get dictionary of elementdata properties
        dd_property_dict = elementData.as_dictionary()
        
        # Get properties from the engine
        properties_list = deviceDetectionCloudEngine.get_properties()

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

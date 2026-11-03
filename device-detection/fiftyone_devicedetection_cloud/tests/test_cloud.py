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

import unittest
import os
import time

from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder

from fiftyone_devicedetection_cloud.devicedetection_cloud import DeviceDetectionCloud

# Resource key environment variables follow the 51Degrees convention, which
# is that every one of them starts with "_51DEGREES_RESOURCE_KEY". The name
# used before the convention was adopted is still read, so an existing setup
# keeps working.
RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"
LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"

MISSING_KEY_MESSAGE = (
    "No resource key found, so the tests that call the cloud service "
    f"cannot run. Set the environment variable '{RESOURCE_KEY_ENV_VAR}' "
    f"(the older name '{LEGACY_RESOURCE_KEY_ENV_VAR}' is still read). "
    "Create a resource key for free at "
    "https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-tests-test_cloud.py&utm_term=resource-key-required")


def get_resource_key():
    """!
    The resource key from the environment, or None when neither the aligned
    nor the older variable is set.
    """

    return (os.environ.get(RESOURCE_KEY_ENV_VAR)
            or os.environ.get(LEGACY_RESOURCE_KEY_ENV_VAR))

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"

cloud_request_origin_test_params = [('', True), ('test.com', True), ('51Degrees.com', False)]

class DeviceDetectionTests(unittest.TestCase):

    def setUp(self):
        self.resource_key = get_resource_key()

        if not self.resource_key:
            self.skipTest(MISSING_KEY_MESSAGE)


    def test_pipeline_builder_cloud_engine_init(self):
        """!
        Tests whether the device detection pipeline builder adds the correct engines when initialised with a resource key
        """

        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        self.assertTrue(pipeline.flow_elements[0].datakey == "cloud")
        self.assertTrue(pipeline.flow_elements[1].datakey == "device")

    def test_properties_cloud(self):
        """!
        Tests whether a properties list is created on the cloud engine
        """
        
        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        properties = pipeline.flow_elements[1].get_properties()

        self.assertTrue(len(properties.keys()) > 0)

    def test_basic_get_cloud(self):
        """!
        Check property lookup works
        """

        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114")

        fd.process()

        self.assertTrue(fd.device.ismobile.value())

    def test_missing_property_service_element_not_found(self):
        """!
        Trigger the missing property service by requesting a property
        not available in any datafile
        """

        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        with self.assertRaises(Exception) as raised:
            fd.get("notpresent")

        result = str(raised.exception)
        self.assertIn("notpresent", result)
        self.assertIn("['device']", result)
        self.assertIn("https://51degrees.com/documentation/_info__resource_keys.html", result)

    def test_engine_init_performance(self):
        """!
        Test how long it takes for the engine to be initialised
        by looking at the metadata dictionary created on init
        """

        start = time.time()

        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        properties = fd.pipeline.get_element("device").get_properties()

        for engine_property in properties:
            self.assertNotEqual(fd.device.get(engine_property), None)

        end = time.time()

        total = end - start

        self.assertLess(total, 10)


    def test_missing_property_service_not_found_anywhere(self):
        """!
        Trigger the missing property service by requesting a property
        not available in cloud
        """

        pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = self.resource_key).build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        with self.assertRaises(Exception) as raised:
            fd.device.get("notpresent")

        result = str(raised.exception)
        self.assertIn("notpresent", result)
        self.assertIn("device", result)
        self.assertIn(', '.join(pipeline.get_element("device").get_properties().keys()), result)
        self.assertIn("https://51degrees.com/documentation/_info__resource_keys.html", result)

    def test_cloud_request_origin(self):
        """!
        Verify that making requests using a resource key that        
        is limited to particular origins will fail or succeed
        in the expected scenarios. 
        This is an integration test that uses the live cloud service
        so any problems with that service could affect the result
        of this test.
        """

        for origin, expectedException in cloud_request_origin_test_params:

            with self.subTest():

                exception = False

                try:
                    pipeline = DeviceDetectionCloudPipelineBuilder(resource_key = "AQS5HKcyVj6B8wNG2Ug", cloud_request_origin = origin).build()

                    fd = pipeline.create_flowdata()

                    fd.evidence.add("header.user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114")

                    fd.process()
                    
                except Exception as e:
                    message = str(e)

                    expectedMessage = "This resource key is not authorised for the domain '{}'.".format(origin)

                    self.assertTrue(message.find(expectedMessage) >= 0, "Exception did not contain expected text ({})".format(message))

                    exception = True

                self.assertEqual(expectedException, exception)

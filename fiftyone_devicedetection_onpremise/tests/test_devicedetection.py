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

import string
import unittest
import os
import time
import csv
import platform

from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder

from fiftyone_devicedetection_onpremise.devicedetection_onpremise import DeviceDetectionOnPremise

from fiftyone_devicedetection_onpremise.devicedetection_datafile import DeviceDetectionDataFile

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.lru_cache import LRUEngineCache

data_file = "src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/51Degrees-LiteV4.1.hash"

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"

# User agents test percentages
minMobilePercentage = 0.72
maxUnknownPercentage = 0.002

# User agents file

with open('src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/20000 User Agents.csv', newline='') as file:
    reader = csv.reader(file)
    user_agents = list(reader)
    no_user_agents = len(user_agents)


class DeviceDetectionTests(unittest.TestCase):

    def test_pipeline_builder_shareusage_init(self):
        """!
        Tests whether the device detection pipeline builder adds the usage sharing engine when initialised with a datafile
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="").build()

        self.assertTrue(pipeline.flow_elements[0].datakey == "shareusage")

    def test_on_premise_engine_datafile(self):
        """!
        Tests whether a datafile (for the update service) is added when auto_update is set
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="test", auto_update=True).build()

        self.assertTrue(isinstance(
            pipeline.flow_elements[0].data_file, DeviceDetectionDataFile))

    def test_properties_onpremise(self):
        """!
        Tests whether a properties list is created on the on
        premise engine
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        properties = pipeline.flow_elements[0].get_properties()

        self.assertTrue(len(properties.keys()) > 0)

    def test_evidencekey_filter_onpremise(self):
        """!
        Tests whether the on premise evidence key filter works
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertFalse(evidence_key_filter.filter_evidence_key("test.test"))
        self.assertTrue(
            evidence_key_filter.filter_evidence_key("header.user-agent"))

    def test_basic_get_onpremise(self):
        """!
        Check property lookup works
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        self.assertTrue(fd.device.ismobile.value())

    def test_process_with_no_evidence(self):
        """!
        Process a FlowData which does not have any evidence. This should not throw an error and all 51Degrees engines should set the default aspect properties
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.process()

        self.assertTrue(fd.device.difference.has_value())

    def test_process_with_empty_user_agent(self):
        """!
        Process a FlowData with an empty user agent
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", "")

        fd.process()

        self.assertFalse(fd.device.ismobile.has_value())

    def test_process_with_no_headers(self):
        """!
        Process a FlowData with no headers
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("irrelevant.evidence", "some-evidence")

        fd.process()

        self.assertFalse(fd.device.ismobile.has_value())

    def test_process_with_no_useful_headers(self):
        """!
        Process a FlowData with no useful headers
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.irrelevant", "some-evidence")

        fd.process()

        self.assertFalse(fd.device.ismobile.has_value())

    def test_case_insensitive_evidence_keys(self):
        """!
        Process a FlowData with case insensitive evidence keys
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        self.assertTrue(fd.device.ismobile.value())

    def test_missing_property_service_not_found_anywhere(self):
        """!
        Trigger the missing property service by requesting a property
        not available in any datafile
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        result = ""

        try:
            fd.device.get("notpresent")
        except Exception as e:
            result = str(e)

        self.assertEqual(
            result, "Property notpresent not found in data for element device. Please check that the element and property names are correct.")

    def test_missing_property_service_not_found_in_current(self):
        """!
        Trigger the missing property service by requesting a property
        not available in the current datafile
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        # Add mock property not in datafile

        pipeline.get_element("device").properties["mock"] = {
            "datafiles": ["Enterprise"]
        }

        fd.process()

        result = ""

        try:
            fd.device.get("mock")
        except Exception as e:
            result = str(e)

        self.assertEqual(
            result, "Property mock not found in data for element device. This is because your datafile does not contain the property. The property is available in['Enterprise']")

    def test_excluded_property(self):
        """!
        Test error if accessing property that has been restricted
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            licence_keys="",
            restricted_properties=["ismobile"]).build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        result = ""

        try:
            fd.device.get("screenpixelsheight")
        except Exception as e:
            result = str(e)

        self.assertEqual(
            result, "Property screenpixelsheight was excluded from device")

    def test_evidencekey_filter_contains_user_agent(self):
        """!
        Test if evidence key filter with header.user-agent
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertTrue(
            evidence_key_filter.filter_evidence_key("header.user-agent"))

    def test_evidencekey_filter_contains_device_stock_ua(self):
        """!
        Test if evidence key filter with header.device-stock-ua
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertTrue(evidence_key_filter.filter_evidence_key(
            "header.device-stock-ua"))

    def test_evidencekey_filter_contains_query_params(self):
        """!
        Test if evidence key filter with query.user-agent query.device-stock-ua
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertTrue(evidence_key_filter.filter_evidence_key(
            "query.device-stock-ua"))
        self.assertTrue(
            evidence_key_filter.filter_evidence_key("query.user-agent"))

    def test_evidencekey_filter_case_insensitive_keys(self):
        """!
        Test evidence key filter with case insensitive keys
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertTrue(
            evidence_key_filter.filter_evidence_key("header.User-Agent"))
        self.assertTrue(
            evidence_key_filter.filter_evidence_key("header.user-agent"))
        self.assertTrue(
            evidence_key_filter.filter_evidence_key("header.USER-AGENT"))
        self.assertTrue(
            evidence_key_filter.filter_evidence_key("HEADER.USER-AGENT"))

    def test_evidencekey_filter_overrides(self):
        """!
        Test evidence key filter with overrides in cookies and query string
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        evidence_key_filter = pipeline.flow_elements[0].get_evidence_key_filter(
        )

        self.assertTrue(evidence_key_filter.filter_evidence_key(
            "query.51d_profileids"))
        self.assertTrue(evidence_key_filter.filter_evidence_key(
            "cookie.51d_profileids"))

    def test_profile_overrides(self):
        """!
        Test profile overrides
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("query.header.user-agent", "Some user agent")

        fd.evidence.add("query.51D_ProfileIds", "12280|17779|17470|18092")

        fd.process()

        self.assertEqual(fd.device.deviceid.value(), "12280-17779-17470-18092")

    def test_profile_overrides_no_headers(self):
        """!
        Test profile overrides no headers
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("query.51D_ProfileIds", "12280|17779|17470|18092")

        fd.process()

        self.assertEqual(fd.device.deviceid.value(), "12280-17779-17470-18092")

    def test_profile_overrides_deviceid(self):
        """!
        Test profile overrides with device ids
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("query.51D_ProfileIds", "12280-17779-17470-18092")

        fd.process()

        self.assertEqual(fd.device.deviceid.value(), "12280-17779-17470-18092")

    def test_device_id(self):
        """!
        Test profile overrides with device ids
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        self.assertEqual(fd.device.deviceid.value(), "12280-81243-82102-18092")

    def test_build_from_config(self):

        config = {
            "PipelineOptions": {
                "Elements": [
                    {
                        "elementName": "DeviceDetectionOnPremise",
                        "elementPath": "fiftyone_devicedetection_onpremise.devicedetection_onpremise",
                        "elementParameters": {
                            "data_file_path": data_file,
                            "licence_keys": ""
                        }
                    }
                ]
            }
        }

        pipeline = PipelineBuilder().build_from_configuration(config)

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.User-Agent", mobile_ua)

        fd.process()

        self.assertTrue(fd.device.ismobile.value())

    def test_no_element_exists(self):
        """!
        Access flow element that doesn't exist in pipeline
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.process()

        message = ""

        try:
            message = fd.devisce
        except Exception as e:
            message = str(e)

        self.assertEqual(
            message, "There is no element data for devisce against this flow data. Available element data keys are: ['device']")

    def test_has_value_false(self):
        """!
        Test aspect property value returns false for has value
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", "?£$%^&*")

        fd.process()

        self.assertFalse(fd.device.ismobile.has_value())

    def test_matched_user_agents(self):
        """!
        Test aspect property value returns false for has value
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        self.assertIsInstance(fd.device.useragents.value(), list)
        # Since the detection result shape was unified in device-detection-cxx
        # (issue #362), a single User-Agent produces one result - and so one
        # matched User-Agent - per component the engine populates, rather than
        # exactly one overall. The number depends on the data file, so assert
        # that at least one is returned.
        self.assertGreaterEqual(len(fd.device.useragents.value()), 1)

    def test_value_types(self):
        """!
        Test type is returned correctly for property
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        ismobile = fd.pipeline.get_element(
            "device").get_properties()["ismobile"]

        self.assertEqual(ismobile["type"], type(
            fd.device.ismobile.value()).__name__)

    def test_available_properties(self):
        """!
        Test properties that come back from getProperties actually exist in engine
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        properties = fd.pipeline.get_element("device").get_properties()

        for engine_property in properties:
            self.assertNotEqual(fd.device.get(engine_property), None)

    def test_engine_init_performance(self):
        """!
        Test how long it takes for the engine to be initialised
        by looking at the metadata dictionary created on init
        """

        start = time.time()

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        properties = fd.pipeline.get_element("device").get_properties()

        for engine_property in properties:
            self.assertNotEqual(fd.device.get(engine_property), None)

        end = time.time()

        total = end - start

        self.assertLess(total, 2 if platform.system() != "Darwin" else 30)

    def test_validate_data_true(self):
        """!
        Validate whether has_value returns correctly with valid evidence
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", mobile_ua)

        fd.process()

        properties = fd.pipeline.get_element("device").get_properties()

        for engine_property in properties:
            data_property = fd.device.get(engine_property)
            if properties[engine_property]["category"] == "Device metrics":
                self.assertEqual(data_property.has_value(), True)
            elif engine_property == "deviceid":
                self.assertEqual(fd.device.deviceid.value(), "0-0-0-0")
            elif engine_property == "javascriptgethighentropyvalues":
                self.assertFalse(data_property.has_value())
            else:
                self.assertEqual(data_property.has_value(), True)

    def test_validate_data_false(self):
        """!
        Validate whether has_value returns correctly with invalid evidence
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.evidence.add("header.user-agent", "")

        fd.process()

        properties = fd.pipeline.get_element("device").get_properties()

        for engine_property in properties:
            data_property = fd.device.get(engine_property)
            if properties[engine_property]["category"] == "Device metrics":
                self.assertEqual(data_property.has_value(), True)
            elif engine_property == "deviceid":
                self.assertEqual(fd.device.deviceid.value(), "0-0-0-0")
            else:
                self.assertEqual(data_property.has_value(), False)

    def test_engine_reload(self):
        """!
        Refresh the engine
        """

        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False, licence_keys="").build()

        fd = pipeline.create_flowdata()

        fd.process()

        fd.pipeline.get_element("device").engine.refreshData()

    def process_user_agent_list(self, pipeline):

        results = {"mobile": 0, "not_mobile": 0, "unknown": 0}

        for user_agent in user_agents:
            user_agent = user_agent[0]
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("header.user-agent", user_agent)
            flowdata.process()

            if flowdata.device.ismobile.has_value():
                if(flowdata.device.ismobile.value()):
                    results["mobile"] += 1
                else:
                    results["not_mobile"] += 1
            else:
                results["unknown"] += 1

        return results


class DeviceDetectionCacheTests(unittest.TestCase):

    def test_engine_refuses_cache_argument(self):
        """!
        Tests that the on-premise engine refuses a cache passed to its
        constructor, because its results read from native memory that
        cannot be shared between requests
        """

        with self.assertRaises(Exception) as context:
            DeviceDetectionOnPremise(
                data_file_path=data_file, licence_keys="",
                cache=LRUEngineCache())

        self.assertIn("results cache", str(context.exception))

    def test_engine_refuses_set_cache(self):
        """!
        Tests that the on-premise engine refuses a cache set on it
        """

        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="")

        with self.assertRaises(Exception) as context:
            engine.set_cache(LRUEngineCache())

        self.assertIn("results cache", str(context.exception))

    def test_pipeline_builder_refuses_cache(self):
        """!
        Tests that the on-premise pipeline builder refuses a cache setting
        """

        with self.assertRaises(Exception) as context:
            DeviceDetectionOnPremisePipelineBuilder(
                data_file_path=data_file, licence_keys="",
                cache=LRUEngineCache()).build()

        self.assertIn("results cache", str(context.exception))

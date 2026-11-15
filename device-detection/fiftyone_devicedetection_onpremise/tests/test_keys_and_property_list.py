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
from unittest.mock import patch

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise import devicedetection_onpremise
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import \
    DeviceDetectionOnPremisePipelineBuilder

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"


class PropertyListTests(unittest.TestCase):
    """!
    A configuration file gives a list of strings as one comma-separated
    string, so restricted_properties takes that form as well as a list.
    """

    def check(self, pipeline):
        self.addCleanup(pipeline.close)
        engine = pipeline.get_element("device")
        self.assertEqual(
            ["IsMobile", "BrowserName"], engine.build_property_names)
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", mobile_ua)
            flowdata.process()
            self.assertTrue(flowdata.device.ismobile.value())

    def test_a_comma_separated_string_names_each_property(self):
        self.check(DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="", usage_sharing=False,
            restricted_properties="IsMobile, BrowserName").build())

    def test_a_configuration_file_names_each_property(self):
        self.check(PipelineBuilder().build_from_configuration({
            "PipelineOptions": {
                "Elements": [{
                    "elementName": "DeviceDetectionOnPremise",
                    "elementPath": "fiftyone_devicedetection_onpremise."
                                   "devicedetection_onpremise",
                    "elementParameters": {
                        "data_file_path": data_file,
                        "licence_keys": "",
                        "restricted_properties": "IsMobile,BrowserName"
                    }
                }]
            }
        }))

    def test_the_callers_list_is_left_as_it_was(self):
        names = ["IsMobile", "BrowserName"]
        self.check(DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="", usage_sharing=False,
            restricted_properties=names).build())
        self.assertEqual(["IsMobile", "BrowserName"], names)

    def test_no_names_builds_the_engine_with_none(self):
        # With no names configured the native engine is given none, rather
        # than the data set's names, and still gives every property.
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="",
            usage_sharing=False).build()
        self.addCleanup(pipeline.close)
        self.assertEqual([], pipeline.get_element("device").build_property_names)
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", mobile_ua)
            flowdata.process()
            self.assertTrue(flowdata.device.ismobile.value())


class EvidenceKeysTests(unittest.TestCase):
    """!
    The Evidence keys come from the data file, so the engine reads them
    at start-up and again whenever the data is refreshed. The engine keeps
    the evidence key filter it makes from the keys, and makes another only
    when the keys change, so a request does not make one for each of its
    Evidence keys.
    """

    def build(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="", usage_sharing=False,
            file_system_watcher=True).build()
        self.addCleanup(pipeline.close)
        return pipeline

    def test_the_keys_are_read_again_when_the_data_is_refreshed(self):
        pipeline = self.build()
        engine = pipeline.get_element("device")
        keys = list(engine.evidence_keys_list)
        self.assertIn("header.user-agent", keys)

        # Stands for the keys of the data loaded before the refresh.
        engine.evidence_keys_list = ["header.x-from-the-earlier-data"]
        engine.data_file.refresh()

        self.assertEqual(keys, engine.evidence_keys_list)

    def test_the_filter_is_kept_until_the_keys_change(self):
        engine = self.build().get_element("device")
        key_filter = engine.get_evidence_key_filter()
        self.assertIs(key_filter, engine.get_evidence_key_filter())
        self.assertTrue(key_filter.filter_evidence_key("Header.User-Agent"))

        # Stands for the keys of the data loaded before the refresh.
        engine.evidence_keys_list = ["header.x-from-the-earlier-data"]
        earlier = engine.get_evidence_key_filter()
        self.assertTrue(
            earlier.filter_evidence_key("header.x-from-the-earlier-data"))
        self.assertFalse(earlier.filter_evidence_key("header.user-agent"))
        self.assertIs(earlier, engine.get_evidence_key_filter())

        engine.data_file.refresh()
        refreshed = engine.get_evidence_key_filter()
        self.assertTrue(refreshed.filter_evidence_key("header.user-agent"))
        self.assertFalse(
            refreshed.filter_evidence_key("header.x-from-the-earlier-data"))
        self.assertIs(refreshed, engine.get_evidence_key_filter())

    def test_a_second_request_makes_no_filter(self):
        pipeline = self.build()

        def process():
            with pipeline.create_flowdata() as flowdata:
                flowdata.evidence.add("header.user-agent", mobile_ua)
                flowdata.process()
                self.assertTrue(flowdata.device.ismobile.value())

        process()
        with patch.object(
                devicedetection_onpremise, "BasicListEvidenceKeyFilter",
                wraps=BasicListEvidenceKeyFilter) as made:
            process()
        self.assertEqual(0, made.call_count)

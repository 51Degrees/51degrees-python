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

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
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


class EvidenceKeysTests(unittest.TestCase):
    """!
    The Evidence keys come from the data file, so the engine reads them
    at start-up and again whenever the data is refreshed.
    """

    def test_the_keys_are_read_again_when_the_data_is_refreshed(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="", usage_sharing=False,
            file_system_watcher=True).build()
        self.addCleanup(pipeline.close)
        engine = pipeline.get_element("device")
        keys = list(engine.evidence_keys_list)
        self.assertIn("header.user-agent", keys)

        # Stands for the keys of the data loaded before the refresh.
        engine.evidence_keys_list = ["header.x-from-the-earlier-data"]
        engine.data_file.refresh()

        self.assertEqual(keys, engine.evidence_keys_list)

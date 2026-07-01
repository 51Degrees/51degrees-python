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
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine

from fiftyone_ipintelligence_cloud.ipintelligence_cloud import IpIntelligenceCloud

from .classes.constants import Constants
from .classes.mockrequestclient import MockRequestClient


class IpIntelligenceCloudTests(unittest.TestCase):

    @staticmethod
    def build_mocked_pipeline():
        cloud_request_engine = CloudRequestEngine({
            "resource_key": Constants.resource_key,
            "http_client": MockRequestClient()
        })

        return (PipelineBuilder()
            .add(cloud_request_engine)
            .add(IpIntelligenceCloud())
            .build())

    def test_datakey(self):
        """!
        The IP intelligence cloud engine extracts the "ip" segment of the
        cloud response (ip-intelligence-dotnet parity).
        """

        engine = IpIntelligenceCloud()
        self.assertEqual(engine.datakey, "ip")

    def test_properties_loaded_from_cloud(self):
        """!
        The engine's property list is populated from the cloud
        accessibleProperties endpoint.
        """

        pipeline = self.build_mocked_pipeline()
        engine = pipeline.flow_elements_list["ip"]

        self.assertIn("RegisteredName", engine.properties)
        self.assertIn("RegisteredCountry", engine.properties)

    def test_process_returns_values(self):
        """!
        Process an IP address and check that freely available values are
        returned.
        """

        pipeline = self.build_mocked_pipeline()

        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.client-ip-51d", Constants.ipv4_address)
        flowdata.process()

        ip_data = flowdata.get("ip")

        registered_name = ip_data.get("registeredname")
        self.assertTrue(registered_name.has_value())
        self.assertEqual(registered_name.value(), "51 Degrees Mobile Experts Limited")

        registered_country = ip_data.get("registeredcountry")
        self.assertTrue(registered_country.has_value())
        self.assertEqual(registered_country.value(), "GB")

    def test_rawweighting_normalised_to_weighting(self):
        """!
        The cloud sends weighted values with a raw 0-65535 "rawweighting"
        field (the same field ip-intelligence-dotnet reads into RawWeighting).
        The engine normalises it to a 0.0-1.0 "weighting" so the shape matches
        the on-premise engine, and the raw field is not leaked to the consumer.
        (Weighted properties are only available on a paid data tier, so this
        normalisation is exercised as a unit test rather than through the free
        cloud mock.)
        """

        normalised = IpIntelligenceCloud._normalise_weighting(
            {"value": "234", "rawweighting": 52428})
        self.assertEqual(normalised["value"], "234")
        self.assertAlmostEqual(normalised["weighting"], 0.8)
        self.assertNotIn("rawweighting", normalised)

        # An entry that already uses "weighting" is left untouched.
        passthrough = IpIntelligenceCloud._normalise_weighting(
            {"value": "235", "weighting": 0.2})
        self.assertEqual(passthrough, {"value": "235", "weighting": 0.2})

    def test_no_value_reason(self):
        """!
        Properties with a null value carry the no-value reason supplied by
        the cloud service.
        """

        pipeline = self.build_mocked_pipeline()

        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.client-ip-51d", Constants.ipv4_address)
        flowdata.process()

        ip = flowdata.ip.get("ip")
        self.assertFalse(ip.has_value())
        self.assertIn("results are empty", ip.no_value_message())


if __name__ == "__main__":
    unittest.main()

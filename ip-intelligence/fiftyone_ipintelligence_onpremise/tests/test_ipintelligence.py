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

from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import IpIntelligenceOnPremise
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder
from fiftyone_pipeline_engines.lru_cache import LRUEngineCache

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the IPINTELLIGENCEDATAFILE environment variable." % data_file)
class IpIntelligenceOnPremiseTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = IpIntelligenceOnPremise(
            data_file_path=data_file,
            licence_keys="")
        cls.pipeline = PipelineBuilder() \
            .add(cls.engine) \
            .build()

    def process(self, key, value):
        flowdata = self.pipeline.create_flowdata()
        flowdata.evidence.add(key, value)
        flowdata.process()
        return flowdata

    def test_engine_init(self):
        """!
        The engine initialises with properties from the data file
        and the synthetic echo properties.
        """

        self.assertEqual(self.engine.datakey, "ip")
        self.assertIn("registeredname", self.engine.properties)
        self.assertIn("registeredcountry", self.engine.properties)
        # Echo properties
        self.assertIn("ip", self.engine.properties)
        self.assertIn("ipv6", self.engine.properties)

    def test_evidence_key_filter(self):
        """!
        The evidence key filter contains the keys reported by the
        native engine.
        """

        evidence_key_filter = self.engine.get_evidence_key_filter()
        self.assertTrue(evidence_key_filter.filter_evidence_key("query.client-ip"))
        self.assertTrue(evidence_key_filter.filter_evidence_key("server.client-ip"))
        self.assertTrue(evidence_key_filter.filter_evidence_key("query.client-ip-51d"))
        self.assertFalse(evidence_key_filter.filter_evidence_key("header.user-agent"))

    def test_process_ipv4(self):
        """!
        Process an IPv4 address and check the network registration
        properties have values.
        """

        flowdata = self.process("query.client-ip", TestConstants.IPV4_ADDRESS)

        registered_name = flowdata.ip.get("registeredname")

        # String properties hold a single value (dotnet parity, weighted
        # properties such as Mcc are returned as lists of
        # {"value", "weighting"} dictionaries).
        self.assertTrue(registered_name.has_value())
        self.assertIsInstance(registered_name.value(), str)
        self.assertGreater(len(registered_name.value()), 0)

    def test_registered_country(self):
        """!
        The registered country is returned as a country code string.
        """

        flowdata = self.process("query.client-ip", TestConstants.IPV4_ADDRESS)

        registered_country = flowdata.ip.get("registeredcountry")
        self.assertTrue(registered_country.has_value())
        self.assertIsInstance(registered_country.value(), str)

    def test_echo_ip(self):
        """!
        The IP address supplied in evidence is echoed back via the
        synthetic Ip property; IpV6 has no value for IPv4 input.
        """

        flowdata = self.process("query.client-ip", TestConstants.IPV4_ADDRESS)

        ip = flowdata.ip.get("ip")
        self.assertTrue(ip.has_value())
        self.assertEqual(ip.value(), TestConstants.IPV4_ADDRESS)

        ipv6 = flowdata.ip.get("ipv6")
        self.assertFalse(ipv6.has_value())

    def test_process_ipv6(self):
        """!
        An IPv6 address can be processed and is echoed back.
        """

        flowdata = self.process("query.client-ip", TestConstants.IPV6_ADDRESS)

        ipv6 = flowdata.ip.get("ipv6")
        self.assertTrue(ipv6.has_value())

    def test_missing_property(self):
        """!
        Accessing a property that does not exist raises an exception
        from the missing property service.
        """

        flowdata = self.process("query.client-ip", TestConstants.IPV4_ADDRESS)

        with self.assertRaises(Exception):
            flowdata.ip.get("notaproperty")

    def test_wrong_data_file_extension(self):
        """!
        The engine only accepts .ipi data files.
        """

        # Use a file that exists but has the wrong extension.
        wrong_file = os.path.join(os.path.dirname(__file__), "constants.py")

        with self.assertRaises(Exception) as context:
            IpIntelligenceOnPremise(
                data_file_path=wrong_file,
                licence_keys="")

        self.assertIn(".ipi", str(context.exception))

    def test_missing_licence_key(self):
        """!
        The engine requires the licence key argument (an empty string
        disables automatic updates).
        """

        with self.assertRaises(Exception) as context:
            IpIntelligenceOnPremise(data_file_path=data_file)

        self.assertIn("licence key is required", str(context.exception))


class CommittedDataFileTests(unittest.TestCase):
    """!
    The native engine accepts exactly one data file format version, so the
    ip-intelligence-cxx pin and the ip-intelligence-data pin must agree.
    They once did not: the engine moved to format 4.6 while the data pin
    still held the 4.5 ASN file. These tests open the ASN file committed to
    the data submodule, which needs no download or secret, so pins that
    disagree fail here on any machine.

    They do not prove the engine reads the data files 51Degrees publishes.
    That is IpIntelligenceOnPremiseTests above, against the Lite or
    Enterprise file CI downloads; it skips when neither is present.
    test_onpremise_datafile_loads in the examples package also opens the
    ASN file, but it skips silently when the file is not found and it runs
    after the examples build, so it is not relied on here.
    """

    def test_committed_data_file_present(self):
        """!
        The committed data file exists. If it does not, the
        ip-intelligence-data submodule was not checked out, and the test
        below would prove nothing.
        """

        self.assertTrue(
            os.path.isfile(TestConstants.get_committed_data_file_path()),
            "Run 'git submodule update --init --recursive'.")

    def test_committed_data_file_opens(self):
        """!
        The engine opens the committed data file, so it reads that file's
        format version, and returns its properties for an IPv4 address.
        """

        engine = IpIntelligenceOnPremise(
            data_file_path=TestConstants.get_committed_data_file_path(),
            licence_keys="")
        pipeline = PipelineBuilder().add(engine).build()

        self.assertIn("asnname", engine.properties)

        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.client-ip", TestConstants.IPV4_ADDRESS)
        flowdata.process()

        self.assertTrue(flowdata.ip.get("asnname").has_value())


if __name__ == "__main__":
    unittest.main()


class IpIntelligenceCacheTests(unittest.TestCase):

    def test_engine_refuses_cache_argument(self):
        """!
        Tests that the on-premise engine refuses a cache passed to its
        constructor, because its results read from native memory that
        cannot be shared between requests
        """

        with self.assertRaises(Exception) as context:
            IpIntelligenceOnPremise(
                data_file_path=data_file, licence_keys="",
                cache=LRUEngineCache())

        self.assertIn("results cache", str(context.exception))

    def test_engine_refuses_set_cache(self):
        """!
        Tests that the on-premise engine refuses a cache set on it
        """

        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="")

        with self.assertRaises(Exception) as context:
            engine.set_cache(LRUEngineCache())

        self.assertIn("results cache", str(context.exception))

    def test_pipeline_builder_refuses_cache(self):
        """!
        Tests that the on-premise pipeline builder refuses a cache setting
        """

        with self.assertRaises(Exception) as context:
            IpIntelligenceOnPremisePipelineBuilder(
                data_file_path=data_file, licence_keys="",
                cache=LRUEngineCache()).build()

        self.assertIn("results cache", str(context.exception))

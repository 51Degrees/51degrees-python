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

from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) AppleWebKit/537"
    ".51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D167 Safari/9537.53")


class EvidenceKeyCaseTests(unittest.TestCase):
    """!
    evidence.md line 10: "Keys MUST be case-insensitive". The native
    evidence matches a key's prefix with case, so a key spelled in another
    case must still reach the native engine. Checked against a real data
    file.
    """

    def setUp(self):
        self.pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file, licence_keys="",
            usage_sharing=False).build()
        self.addCleanup(self.pipeline.close)

    def is_mobile(self, key):
        flowdata = self.pipeline.create_flowdata()
        flowdata.evidence.add(key, MOBILE_USER_AGENT)
        flowdata.process()
        return flowdata.device.ismobile

    def test_a_key_in_any_case_reaches_the_native_engine(self):
        for key in ("Header.User-Agent", "HEADER.USER-AGENT",
                    "Query.User-Agent"):
            with self.subTest(key=key):
                expected = self.is_mobile(key.lower())
                actual = self.is_mobile(key)
                self.assertTrue(expected.has_value())
                self.assertTrue(actual.has_value())
                self.assertEqual(expected.value(), actual.value())


if __name__ == "__main__":
    unittest.main()

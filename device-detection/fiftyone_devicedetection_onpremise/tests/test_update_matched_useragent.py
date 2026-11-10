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

from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder

# The free Lite data file, where cxx/data/get-data-files.ps1 and
# get-data-files.sh download it and where CI links it in.
DATA_FILE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cxx",
    "data", "device-detection", "51Degrees-LiteV4.1.hash"))

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) "
    "AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114")

# The character the native code writes where the evidence was not matched.
UNMATCHED = "_"


@unittest.skipUnless(
    os.path.isfile(DATA_FILE),
    "The free Lite data file is not at {0}. Download it with "
    "cxx/data/get-data-files.ps1 or cxx/data/get-data-files.sh, after "
    "'git submodule update --init --recursive'.".format(DATA_FILE))
class UpdateMatchedUserAgentTests(unittest.TestCase):
    """
    The Update Matched User Agent option is on unless it is turned off, so
    the UserAgents property holds the characters of the evidence that were
    matched.
    """

    def _user_agents(self, **settings):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=DATA_FILE, usage_sharing=False, licence_keys="",
            **settings).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        self.addCleanup(flowdata.close)
        flowdata.evidence.add("header.user-agent", MOBILE_UA)
        flowdata.process()
        return flowdata.device.useragents.value()

    def assert_matched_from_the_evidence(self, user_agents):
        """
        Each matched User-Agent has the evidence's characters where they were
        matched, and at least one character was matched.
        """
        self.assertGreaterEqual(len(user_agents), 1)
        matched = 0
        for user_agent in user_agents:
            for index, character in enumerate(user_agent):
                if character != UNMATCHED:
                    self.assertEqual(MOBILE_UA[index], character, user_agent)
                    matched += 1
        self.assertGreater(matched, 0, user_agents)

    def test_builder_defaults_populate_user_agents(self):
        self.assert_matched_from_the_evidence(self._user_agents())

    def test_turned_on_populates_user_agents(self):
        self.assert_matched_from_the_evidence(
            self._user_agents(update_matched_useragent=True))

    def test_turned_off_leaves_user_agents_empty(self):
        user_agents = self._user_agents(update_matched_useragent=False)
        self.assertGreaterEqual(len(user_agents), 1)
        self.assertEqual([""] * len(user_agents), user_agents)

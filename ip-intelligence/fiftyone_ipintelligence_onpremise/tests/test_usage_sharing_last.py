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

"""
The on-premise builder puts the usage sharing element after every other Flow
Element, those the caller adds once the builder is made included.
"""

import os
import unittest

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder

from .constants import TestConstants

# The free ASN data file, which needs no licence key.
DATA_FILE = os.path.normpath(TestConstants.get_asn_data_file_path())


class AddedElement(FlowElement):
    def __init__(self):
        super(AddedElement, self).__init__()
        self.datakey = "added"


@unittest.skipUnless(
    os.path.isfile(DATA_FILE),
    "The free ASN data file is not at {0}.".format(DATA_FILE))
class UsageSharingLastTests(unittest.TestCase):

    def datakeys(self, builder):
        pipeline = builder.build()
        self.addCleanup(pipeline.close)
        return [element.datakey for element in pipeline.flow_elements]

    def builder(self, **settings):
        return IpIntelligenceOnPremisePipelineBuilder(
            data_file_path=DATA_FILE, licence_keys="",
            performance_profile="LowMemory", **settings)

    def test_usage_sharing_is_last(self):
        self.assertEqual(
            ["sequence", "ip", "jsonbundler", "javascriptbuilder",
             "set-headers", "shareusage"],
            self.datakeys(self.builder()))

    def test_usage_sharing_follows_an_element_added_later(self):
        self.assertEqual(
            ["sequence", "ip", "added", "jsonbundler", "javascriptbuilder",
             "set-headers", "shareusage"],
            self.datakeys(self.builder().add(AddedElement())))

    def test_no_usage_sharing_when_it_is_off(self):
        self.assertEqual(
            ["sequence", "ip", "jsonbundler", "javascriptbuilder",
             "set-headers"],
            self.datakeys(self.builder(usage_sharing=False)))


if __name__ == "__main__":
    unittest.main()

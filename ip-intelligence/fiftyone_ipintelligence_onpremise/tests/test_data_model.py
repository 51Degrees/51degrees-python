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
The element data the on-premise IP Intelligence engine gives, as the user
facing structure section of the IP Intelligence data model specification
says.
"""

import os
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.aspectdata import AspectData

from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import \
    IpIntelligenceOnPremise

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the _51DEGREES_IPI_PATH environment variable." % data_file)
class IpIntelligenceDataModelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = IpIntelligenceOnPremise(
            data_file_path=data_file,
            licence_keys="")
        cls.pipeline = PipelineBuilder() \
            .add(cls.engine) \
            .build()

    @classmethod
    def tearDownClass(cls):
        cls.pipeline.close()

    def process(self, address):
        flowdata = self.pipeline.create_flowdata()
        self.addCleanup(flowdata.close)
        flowdata.evidence.add("query.client-ip", address)
        flowdata.process()
        return flowdata

    def test_element_data_is_aspect_data(self):
        """!
        The element data for an IPv4 and an IPv6 address is Aspect Data.
        """

        for address in (TestConstants.IPV4_ADDRESS,
                        TestConstants.IPV6_ADDRESS):
            with self.subTest(address=address):
                flowdata = self.process(address)
                self.assertIsInstance(
                    flowdata.get(self.engine.datakey), AspectData)


if __name__ == "__main__":
    unittest.main()

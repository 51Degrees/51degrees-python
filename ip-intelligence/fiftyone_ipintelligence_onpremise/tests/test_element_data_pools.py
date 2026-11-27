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
The engine takes its ElementData from a pool, as the resource cleanup page
of the specification describes, so over many requests, each closing its
FlowData, it makes one instance rather than one for each request, and a
reused instance gives the new request's results with none of the last.
"""

import unittest
from unittest import mock

from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import \
    IpIntelligenceOnPremise
from fiftyone_ipintelligence_onpremise.swig_data import SwigData
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .constants import TestConstants

DATA_FILE = TestConstants.get_data_file_path()

# Far more requests than the pool's bound.
REQUESTS = 200


class ElementDataPoolTests(unittest.TestCase):

    def setUp(self):
        engine = IpIntelligenceOnPremise(
            data_file_path=DATA_FILE, licence_keys="", auto_update=False)
        self.pipeline = PipelineBuilder({"add_javascript_builder": False,
                                         "use_setheader_properties": False}) \
            .add(engine).build()
        self.addCleanup(self.pipeline.close)

    def process(self, address):
        flowdata = self.pipeline.create_flowdata()
        flowdata.evidence.add("query.client-ip", address)
        flowdata.process()
        return flowdata

    def test_one_instance_is_made_over_many_requests(self):
        made = []
        original = SwigData.__init__

        def counting(data, *args, **kwargs):
            made.append(data)
            original(data, *args, **kwargs)

        with mock.patch.object(SwigData, "__init__", counting):
            for _ in range(REQUESTS):
                with self.process(TestConstants.IPV4_ADDRESS) as flowdata:
                    self.assertEqual(TestConstants.IPV4_ADDRESS,
                                     flowdata.ip.get("ip").value())
        self.assertEqual(1, len(made))

    def test_a_reused_instance_has_no_address_from_the_last_request(self):
        with self.process(TestConstants.IPV4_ADDRESS) as flowdata:
            first = flowdata.ip
            self.assertTrue(first.get("ip").has_value())
        with self.process(TestConstants.IPV6_ADDRESS) as flowdata:
            self.assertIs(first, flowdata.ip)
            self.assertFalse(flowdata.ip.get("ip").has_value())
            self.assertEqual(TestConstants.IPV6_ADDRESS,
                             flowdata.ip.get("ipv6").value())
            self.assertEqual({}, flowdata.errors)


if __name__ == "__main__":
    unittest.main()

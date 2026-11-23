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
reused instance gives the new request's results.
"""

import unittest
from unittest import mock

from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise
from fiftyone_devicedetection_onpremise.swig_data import SwigData
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

DATA_FILE = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Far more requests than the pool's bound.
REQUESTS = 200


class ElementDataPoolTests(unittest.TestCase):

    def setUp(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=DATA_FILE, licence_keys="", auto_update=False)
        self.pipeline = PipelineBuilder({"add_javascript_builder": False,
                                         "use_setheader_properties": False}) \
            .add(engine).build()
        self.addCleanup(self.pipeline.close)

    def process(self, user_agent):
        flowdata = self.pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", user_agent)
        flowdata.process()
        return flowdata

    def test_one_instance_is_made_over_many_requests(self):
        made = []
        original = SwigData.__init__

        def counting(data, *args, **kwargs):
            made.append(data)
            original(data, *args, **kwargs)

        with mock.patch.object(SwigData, "__init__", counting):
            for index in range(REQUESTS):
                user_agent = MOBILE if index % 2 else DESKTOP
                with self.process(user_agent) as flowdata:
                    self.assertEqual(bool(index % 2),
                                     flowdata.device.ismobile.value())
        self.assertEqual(1, len(made))

    def test_a_reused_instance_gives_the_new_request_results(self):
        with self.process(MOBILE) as flowdata:
            first = flowdata.device
            self.assertTrue(first.ismobile.value())
        with self.process(DESKTOP) as flowdata:
            self.assertIs(first, flowdata.device)
            self.assertFalse(flowdata.device.ismobile.value())
            self.assertEqual({}, flowdata.errors)


if __name__ == "__main__":
    unittest.main()

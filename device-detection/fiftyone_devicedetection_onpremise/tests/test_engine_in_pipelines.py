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
One on-premise Device Detection engine in two Pipelines. The native engine
is built once, so a second Pipeline neither loads the data file again nor
replaces the engine the first Pipeline uses.
"""

import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) "
             "AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114")
SETTINGS = {"add_javascript_builder": False, "use_setheader_properties": False}


def is_mobile(pipeline):
    with pipeline.create_flowdata() as flowdata:
        flowdata.evidence.add("header.user-agent", mobile_ua)
        flowdata.process()
        return flowdata.device.ismobile.value()


class EngineInPipelinesTests(unittest.TestCase):

    def test_a_second_pipeline_uses_the_engine_already_built(self):
        element = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        self.addCleanup(element.close)
        first = PipelineBuilder(SETTINGS).add(element).build()
        native = element.engine

        second = PipelineBuilder(SETTINGS).add(element).build()

        self.assertIs(native, element.engine)
        for pipeline in (first, second):
            self.assertIs(True, is_mobile(pipeline))


if __name__ == "__main__":
    unittest.main()

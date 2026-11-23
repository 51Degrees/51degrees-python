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

"""The JSON Builder leaves the Cloud Request Engine's Element Data out of the
JSON, as the JSON Builder specification says."""

import unittest

from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class StandInCloudRequestEngine(FlowElement):
    """Writes the raw answer under the Cloud Request Engine's data key."""

    def __init__(self):
        super(StandInCloudRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.properties = {"cloud": {"name": "cloud", "type": "string"}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"cloud": '{"device":{"ismobile":true}}'}))


class JsonBuilderExcludesTests(unittest.TestCase):

    def test_the_cloud_request_engine_is_left_out(self):
        pipeline = PipelineBuilder({}).add(StandInCloudRequestEngine()) \
            .build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        self.assertNotIn("cloud", flowdata.jsonbundler.json)


if __name__ == "__main__":
    unittest.main()

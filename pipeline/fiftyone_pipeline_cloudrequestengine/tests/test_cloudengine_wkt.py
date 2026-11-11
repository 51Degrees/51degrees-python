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
A WKT value in a response from the remote server is an object with one member,
value, holding the WKT text, and the engine gives the text.
"""

import json
import unittest

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

AREA = "POLYGON((1 2, 3 4, 5 6, 1 2))"


class FakeCloudRequestEngine(FlowElement):

    def __init__(self, answer):
        super(FakeCloudRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.answer = answer
        # Keyed by the names the cloud service gives, as
        # CloudRequestEngine.get_engine_properties keys them.
        self.flow_element_properties = {
            "ip": {"Areas": {"name": "Areas", "type": "WktString"},
                   "Name": {"name": "Name", "type": "String"}}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"cloud": json.dumps(self.answer)}))


def read(answer):
    engine = CloudEngine()
    engine.datakey = "ip"
    pipeline = PipelineBuilder({
        "add_javascript_builder": False, "use_setheader_properties": False}) \
        .add(FakeCloudRequestEngine(answer)).add(engine).build()
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    pipeline.close()
    return flowdata.get("ip")


class CloudEngineWktTests(unittest.TestCase):

    def test_the_text_is_taken_out_of_the_object(self):
        data = read({"ip": {"areas": {"value": AREA}, "name": "a place"}})
        self.assertEqual(AREA, data.get("areas").value())
        self.assertEqual("a place", data.get("name").value())

    def test_text_that_is_already_plain_is_kept(self):
        data = read({"ip": {"areas": AREA, "name": "a place"}})
        self.assertEqual(AREA, data.get("areas").value())


if __name__ == "__main__":
    unittest.main()

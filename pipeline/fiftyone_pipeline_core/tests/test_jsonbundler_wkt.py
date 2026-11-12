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
A WKT value is written to JSON as an object with one member, value, holding
the WKT text, as the value types page of the specification says.
"""

import unittest

from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

AREA = "POLYGON((1 2, 3 4, 5 6, 1 2))"


class AreasElement(FlowElement):

    def __init__(self, type_name):
        super(AreasElement, self).__init__()
        self.datakey = "areas"
        self.properties = {
            "areas": {"name": "Areas", "type": type_name},
            "name": {"name": "Name", "type": "string"}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"Areas": AREA, "Name": "a place"}))


def json_of(type_name):
    pipeline = PipelineBuilder({}).add(AreasElement(type_name)).build()
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    pipeline.close()
    return flowdata.jsonbundler.json["areas"]


class JsonBuilderWktTests(unittest.TestCase):

    def test_a_wkt_value_is_an_object_holding_the_text(self):
        for type_name in ("WktString", "wkb", "WKBR", "wkt"):
            self.assertEqual(
                {"value": AREA}, json_of(type_name)["areas"], type_name)

    def test_other_values_are_written_as_they_are(self):
        self.assertEqual("a place", json_of("WktString")["name"])


if __name__ == "__main__":
    unittest.main()

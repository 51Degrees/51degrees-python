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
Element options set from a configuration file, as the Flow Elements section
of the pipeline configuration feature specification says.
"""

import json
import os
import tempfile
import unittest

from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

UPDATE_URL = "http://127.0.0.1:9/update"


class Configured(FlowElement):
    """!
    An element whose options, a string, a number and a boolean, each change
    the message it gives, and which keeps the two data update options that
    have older names.
    """

    def __init__(
            self, greeting="hello", repeat=1, shout=False,
            data_update_url=None, data_update_verify_md5=True):
        super(Configured, self).__init__()
        self.datakey = "configured"
        self.properties = {"message": {"type": "string"}}
        self.greeting = greeting
        self.repeat = repeat
        self.shout = shout
        self.data_update_url = data_update_url
        self.data_update_verify_md5 = data_update_verify_md5

    def process_internal(self, flow_data):
        message = " ".join([self.greeting] * self.repeat)
        if self.shout:
            message = message.upper()
        flow_data.set_element_data(
            ElementDataDictionary(self, {"message": message}))


class PipelineConfigurationTests(unittest.TestCase):

    def build_from_file(self, parameters):
        """!
        Write a configuration file that adds a Configured element with the
        parameters, read it back and build the pipeline it describes.
        """
        configuration = {
            "PipelineOptions": {
                "Elements": [
                    {
                        "elementName": Configured.__name__,
                        "elementPath": __name__,
                        "elementParameters": parameters,
                    }
                ]
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "pipeline.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(configuration, file)
            with open(path, encoding="utf-8") as file:
                configuration = json.load(file)
        return PipelineBuilder().build_from_configuration(configuration)

    def message(self, pipeline):
        flow_data = pipeline.create_flowdata()
        flow_data.process()
        return flow_data.get("configured").get("message")

    def test_options_from_a_file_use_the_names_in_code(self):
        """!
        Options given in a configuration file under the names the element
        takes in code reach it under those names and take effect, the same
        as when it is configured in code.
        """

        pipeline = self.build_from_file(
            {"greeting": "good day", "repeat": 2, "shout": True})
        in_code = PipelineBuilder(
            {"add_javascript_builder": False,
             "use_setheader_properties": False}) \
            .add(Configured(greeting="good day", repeat=2, shout=True)) \
            .build()

        element = pipeline.get_element("configured")
        self.assertEqual("good day", element.greeting)
        self.assertEqual(2, element.repeat)
        self.assertTrue(element.shout)
        self.assertEqual("GOOD DAY GOOD DAY", self.message(pipeline))
        self.assertEqual(self.message(in_code), self.message(pipeline))

    def test_older_option_names_still_reach_the_element(self):
        """!
        The older names verify_md5 and data_file_update_base_url, given in
        a configuration file, reach the element as data_update_verify_md5
        and data_update_url. The value given differs from the default, so
        the test passes only when the name is mapped.
        """

        pipeline = self.build_from_file(
            {"verify_md5": False, "data_file_update_base_url": UPDATE_URL})

        element = pipeline.get_element("configured")
        self.assertFalse(element.data_update_verify_md5)
        self.assertEqual(UPDATE_URL, element.data_update_url)

    def test_newer_option_names_reach_the_element(self):
        """!
        The current names of the two data update options reach the element
        unchanged.
        """

        pipeline = self.build_from_file(
            {"data_update_verify_md5": False, "data_update_url": UPDATE_URL})

        element = pipeline.get_element("configured")
        self.assertFalse(element.data_update_verify_md5)
        self.assertEqual(UPDATE_URL, element.data_update_url)


if __name__ == "__main__":
    unittest.main()

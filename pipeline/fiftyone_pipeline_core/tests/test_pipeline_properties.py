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
Property metadata at the Pipeline level, as the property metadata section of
the properties feature specification says.
"""

import unittest

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# No JavaScript or set header elements, so the pipeline holds only the
# elements a test adds.
NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

FIRST_PROPERTIES = {
    "IsMobile": {"type": "bool", "category": "Device",
                 "description": "Whether the device is a mobile device."},
    "ScreenWidth": {"type": "int", "category": "Screen",
                    "description": "The width of the screen in pixels."},
}

SECOND_PROPERTIES = {
    "Country": {"type": "string", "category": "Location",
                "description": "The country the request came from."},
}


class First(FlowElement):
    """!
    An element with two properties, whose metadata it holds from the start.
    """

    def __init__(self):
        super(First, self).__init__()
        self.datakey = "first"
        self.properties = FIRST_PROPERTIES


class Second(FlowElement):
    """!
    An element with one property, whose metadata it holds from the start.
    """

    def __init__(self):
        super(Second, self).__init__()
        self.datakey = "second"
        self.properties = SECOND_PROPERTIES


class PipelinePropertiesTests(unittest.TestCase):

    def test_metadata_of_every_property_of_both_elements(self):
        """!
        The pipeline gives the metadata of every property of both of its
        elements, keyed by each element's data key and then by the
        property's name in lower case, without processing anything.
        """

        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add(First()).add(Second()).build()

        self.assertEqual(
            {
                "first": {
                    "ismobile": FIRST_PROPERTIES["IsMobile"],
                    "screenwidth": FIRST_PROPERTIES["ScreenWidth"],
                },
                "second": {
                    "country": SECOND_PROPERTIES["Country"],
                },
            },
            pipeline.get_properties())

    def test_metadata_of_the_elements_the_builder_adds(self):
        """!
        The elements the builder adds by default are in the pipeline too, so
        the pipeline gives their metadata, the same as each element gives.
        """

        pipeline = PipelineBuilder().add(First()).add(Second()).build()

        properties = pipeline.get_properties()

        self.assertEqual(
            [element.datakey for element in pipeline.flow_elements],
            list(properties))
        for element in pipeline.flow_elements:
            with self.subTest(element=element.datakey):
                self.assertEqual(
                    element.get_properties(), properties[element.datakey])


if __name__ == "__main__":
    unittest.main()

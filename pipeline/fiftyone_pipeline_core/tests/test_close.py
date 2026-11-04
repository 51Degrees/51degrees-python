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

import unittest

from fiftyone_pipeline_core.elementdata import ElementData
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class ClosingData(ElementData):
    """Element data with a close method of its own, as the results of an
    on-premise engine have."""

    def __init__(self, flow_element):
        super(ClosingData, self).__init__(flow_element)
        self.closed = False

    def close(self):
        self.closed = True


class ClosingElement(FlowElement):
    """Adds ClosingData to each FlowData, and counts its own closes."""

    def __init__(self):
        super(ClosingElement, self).__init__()
        self.datakey = "closing"
        self.closes = 0

    def process_internal(self, flowdata):
        flowdata.set_element_data(ClosingData(self))

    def close(self):
        self.closes += 1


class PlainElement(FlowElement):
    """Adds element data that needs no cleanup."""

    def __init__(self):
        super(PlainElement, self).__init__()
        self.datakey = "plain"

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {"close": 1}))


class FailingElement(FlowElement):
    """Fails to close."""

    def __init__(self):
        super(FailingElement, self).__init__()
        self.datakey = "failing"

    def close(self):
        raise Exception("close failed")


class RecordedElement(FlowElement):
    """Records each instance that is closed, for a test whose pipeline
    failed to build and so cannot be reached."""

    closed = []

    def __init__(self):
        super(RecordedElement, self).__init__()
        self.datakey = "recorded"

    def close(self):
        RecordedElement.closed.append(self)


class BrokenElement(FlowElement):
    """Fails to build."""

    def __init__(self):
        raise ValueError("element failed to build")


def build(*elements, **settings):
    settings["add_javascript_builder"] = False
    settings["use_setheader_properties"] = False
    builder = PipelineBuilder(settings)
    for element in elements:
        builder.add(element)
    return builder.build()


class CloseTests(unittest.TestCase):

    # Element data with a close method is closed with the FlowData, and
    # element data without one is left alone, even with a property called
    # close.
    def test_flowdata_closes_element_data(self):
        with build(ClosingElement(), PlainElement()) as pipeline:
            with pipeline.create_flowdata() as flowdata:
                flowdata.process()
                closing = flowdata.get("closing")
                self.assertFalse(closing.closed)
            self.assertTrue(closing.closed)
            self.assertEqual(1, flowdata.get("plain").get("close"))

    # The with statement closes the FlowData when an exception is raised.
    def test_flowdata_closed_on_exception(self):
        with build(ClosingElement()) as pipeline:
            with self.assertRaises(ValueError):
                with pipeline.create_flowdata() as flowdata:
                    flowdata.process()
                    closing = flowdata.get("closing")
                    raise ValueError()
            self.assertTrue(closing.closed)

    # A FlowData that was never processed holds nothing to close.
    def test_unprocessed_flowdata_closes(self):
        with build(ClosingElement()) as pipeline:
            pipeline.create_flowdata().close()

    def test_pipeline_closes_elements(self):
        element = ClosingElement()
        with build(element):
            self.assertEqual(0, element.closes)
        self.assertEqual(1, element.closes)

    # Elements shared with another pipeline are left for the caller to
    # close.
    def test_pipeline_leaves_elements_open(self):
        element = ClosingElement()
        with build(element, auto_close_elements=False):
            pass
        self.assertEqual(0, element.closes)

    # Every element is closed even when one fails, and the failure is
    # raised afterwards.
    def test_pipeline_closes_every_element(self):
        element = ClosingElement()
        pipeline = build(FailingElement(), element)
        with self.assertRaises(Exception) as context:
            pipeline.close()
        self.assertEqual("close failed", str(context.exception))
        self.assertEqual(1, element.closes)

    # When an element in a configuration fails to build, the elements built
    # before it are closed, and the error that stopped the build is raised.
    def test_failed_configuration_closes_built_elements(self):
        RecordedElement.closed = []
        config = {
            "PipelineOptions": {
                "Elements": [
                    {"elementName": "RecordedElement", "elementPath": __name__},
                    {"elementName": "BrokenElement", "elementPath": __name__}
                ]
            }
        }
        with self.assertRaises(ValueError) as context:
            PipelineBuilder().build_from_configuration(config)
        self.assertEqual("element failed to build", str(context.exception))
        self.assertEqual(1, len(RecordedElement.closed))


if __name__ == "__main__":
    unittest.main()

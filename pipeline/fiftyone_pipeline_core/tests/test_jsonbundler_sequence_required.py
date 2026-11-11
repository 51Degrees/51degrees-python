
"""
The JSON Builder fails with an error, and sets no JSON, when no Sequence
Element has produced a sequence number, as the JSON Builder specification
says.
"""

import unittest

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.jsonbundler import JSONBundlerElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class KeepsTheSequence(FlowElement):
    """Accepts query.sequence and does nothing else, as an element of the
    caller's that keeps the integer it adds would. The JSON Builder accepts
    no evidence, so without such an element the pipeline sets the value
    aside."""

    def __init__(self):
        super(KeepsTheSequence, self).__init__()
        self.datakey = "keepsthesequence"

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["query.sequence"])

    def process_internal(self, flowdata):
        pass


def bundler_only(suppress=False, keep_sequence=False):
    builder = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False,
        "suppress_process_exceptions": suppress})
    if keep_sequence:
        builder.add(KeepsTheSequence())
    return builder.add(JSONBundlerElement()).build()


class JsonBuilderSequenceTests(unittest.TestCase):

    def test_no_sequence_number_is_an_error_that_names_the_sequence_element(
            self):
        pipeline = bundler_only()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        with self.assertRaises(Exception) as caught:
            flowdata.process()
        self.assertEqual(
            "The JSON Builder needs a sequence number. Place a Sequence "
            "Element before the JSON Builder in the Pipeline.",
            str(caught.exception))

    def test_no_json_is_set_when_the_error_is_suppressed(self):
        pipeline = bundler_only(suppress=True)
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        self.assertEqual(1, len(flowdata.errors))
        self.assertNotIn("jsonbundler", flowdata.data)

    def test_a_sequence_number_from_the_query_string_does_not_count(self):
        for value in ("3", "", "abc", True, 3.0):
            pipeline = bundler_only(suppress=True)
            self.addCleanup(pipeline.close)
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("query.sequence", value)
            flowdata.process()
            self.assertEqual(1, len(flowdata.errors), repr(value))
            self.assertNotIn("jsonbundler", flowdata.data, repr(value))

    def test_an_integer_sequence_number_in_the_evidence_counts(self):
        pipeline = bundler_only(keep_sequence=True)
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.sequence", 3)
        flowdata.process()
        self.assertIn("javascriptProperties", flowdata.jsonbundler.json)

    def test_the_default_pipeline_has_a_sequence_number(self):
        pipeline = PipelineBuilder({}).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.process()
        self.assertEqual(0, len(flowdata.errors))
        self.assertIn("javascriptProperties", flowdata.jsonbundler.json)

    def test_a_sequence_of_ten_or_more_leaves_out_the_javascript_properties(
            self):
        pipeline = bundler_only(keep_sequence=True)
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.sequence", 10)
        flowdata.process()
        self.assertEqual([], flowdata.jsonbundler.json["javascriptProperties"])


if __name__ == "__main__":
    unittest.main()

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

"""Step 5 of the JavaScript Builder specification's process takes the session
id and the sequence from the Sequence Element's Element Data, and where there
is no Sequence Element renders the sequence as 1 and the session id as an
empty string, whatever the evidence holds. Both sides of that branch are
tested here, and so is the source the values are read from, because the
builder used to read them from Evidence instead."""

import re
import unittest

from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.javascriptbuilder import JavascriptBuilderElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.sequenceelement import SequenceElement


class StandInJsonBuilder(FlowElement):
    """Gives the JavaScript Builder its JSON without needing a sequence."""

    def __init__(self):
        super(StandInJsonBuilder, self).__init__()
        self.datakey = "jsonbundler"
        self.properties = {"json": {"type": "dict"}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"json": {"javascriptProperties": []}}))


class StandInSequenceElement(FlowElement):
    """Takes the place of the SequenceElement, writing one pair into its
    Element Data and a different pair into Evidence, so that a test can tell
    which of the two the builder read. Element Data of None stands for an
    element that is in the pipeline and produced nothing."""

    def __init__(self, contents):
        super(StandInSequenceElement, self).__init__()
        self.datakey = "sequence"
        self.contents = contents

    def process_internal(self, flowdata):
        flowdata.evidence.add("query.session-id", "from-evidence")
        flowdata.evidence.add("query.sequence", 99)
        if self.contents is not None:
            flowdata.set_element_data(
                ElementDataDictionary(self, self.contents))


def render(evidence, sequence_element=False, stand_in=None):
    """Render the script from a pipeline that differs only in which Sequence
    Element it holds, if any. The real JSON bundler refuses a pipeline with no
    sequence number, so a stand-in gives the builder its JSON."""

    builder = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False})
    if sequence_element:
        builder = builder.add(SequenceElement())
    if stand_in is not None:
        builder = builder.add(stand_in)
    pipeline = builder \
        .add(StandInJsonBuilder()) \
        .add(JavascriptBuilderElement({"minify": False})) \
        .build()
    flowdata = pipeline.create_flowdata()
    for key, value in evidence.items():
        flowdata.evidence.add(key, value)
    flowdata.process()
    return flowdata.javascriptbuilder.javascript


def line(script, name):
    return [text.strip() for text in script.splitlines()
            if re.match(r"\s*var " + name + r"\s*=", text)]


class NoSequenceElementTests(unittest.TestCase):

    def test_the_sequence_is_one_and_the_session_id_empty(self):
        script = render({"query.sequence": "5",
                         "query.session-id": "abc-123"})
        self.assertEqual(["var sequence = 1;"], line(script, "sequence"))
        self.assertEqual(['var sessionId = "";'], line(script, "sessionId"))

    def test_an_empty_request_gives_the_same_defaults(self):
        script = render({})
        self.assertEqual(["var sequence = 1;"], line(script, "sequence"))
        self.assertEqual(['var sessionId = "";'], line(script, "sessionId"))

    def test_a_session_id_the_builder_would_accept_is_still_left_out(self):
        """A session id that passes the builder's own check is rendered
        empty, so the empty string comes from there being no Sequence
        Element rather than from that check."""

        script = render({"query.session-id": "a" * 64})
        self.assertEqual(['var sessionId = "";'], line(script, "sessionId"))

    def test_with_a_sequence_element_its_values_are_rendered(self):
        """The same pipeline with a SequenceElement renders what that element
        produced, which is the request's sequence counted on by one and the
        session id it was given."""

        script = render({"query.sequence": "5",
                         "query.session-id": "abc-123"},
                        sequence_element=True)
        self.assertEqual(["var sequence = 6;"], line(script, "sequence"))
        self.assertEqual(
            ['var sessionId = "abc-123";'], line(script, "sessionId"))


class WhereTheValuesComeFromTests(unittest.TestCase):

    def test_the_element_data_is_read_and_the_evidence_is_not(self):
        """The stand-in puts one pair in its Element Data and a different
        pair in Evidence. What is rendered says which of the two was read."""

        script = render({}, stand_in=StandInSequenceElement(
            {"session-id": "from-element-data", "sequence": 7}))
        self.assertEqual(["var sequence = 7;"], line(script, "sequence"))
        self.assertEqual(
            ['var sessionId = "from-element-data";'],
            line(script, "sessionId"))

    def test_an_element_that_produced_no_element_data_gives_the_defaults(self):
        """A Sequence Element that is in the pipeline but set no Element
        Data, because it stopped or failed, is the same as no Sequence
        Element at all, so the script still parses."""

        script = render({}, stand_in=StandInSequenceElement(None))
        self.assertEqual(["var sequence = 1;"], line(script, "sequence"))
        self.assertEqual(['var sessionId = "";'], line(script, "sessionId"))

    def test_an_unusable_pair_in_the_element_data_is_rendered_safely(self):
        """The session id is written inside quotes and the sequence as bare
        code, so a session id that does not match the pattern is rendered
        empty and a sequence that is not a positive 32 bit integer is 1."""

        script = render({}, stand_in=StandInSequenceElement(
            {"session-id": 'a" + alert(1) + "', "sequence": "not a number"}))
        self.assertEqual(["var sequence = 1;"], line(script, "sequence"))
        self.assertEqual(['var sessionId = "";'], line(script, "sessionId"))

    def test_the_sequence_element_publishes_the_pair_it_wrote(self):
        """The real SequenceElement's Element Data holds the same session id
        and sequence it put in Evidence, which is what the builder reads."""

        builder = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False})
        pipeline = builder.add(SequenceElement()).build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.session-id", "abc-123")
        flowdata.evidence.add("query.sequence", "5")
        flowdata.process()

        self.assertEqual("abc-123", flowdata.sequence.get("session-id"))
        self.assertEqual(6, flowdata.sequence.get("sequence"))
        self.assertEqual(
            flowdata.evidence.get("query.session-id"),
            flowdata.sequence.get("session-id"))
        self.assertEqual(
            flowdata.evidence.get("query.sequence"),
            flowdata.sequence.get("sequence"))


if __name__ == "__main__":
    unittest.main()

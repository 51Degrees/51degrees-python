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

"""With no Sequence Element in the pipeline, the JavaScript Builder renders
the sequence as 1 and the session id as an empty string, as step 5 of the
JavaScript Builder specification's process says, whatever the evidence
holds. The same pipeline with a Sequence Element renders that element's
values, which is the other side of the same branch."""

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


def render(evidence, sequence_element=False):
    """Render the script from a pipeline that differs only in whether it
    holds a SequenceElement. The real JSON bundler refuses a pipeline with no
    sequence number, so a stand-in gives the builder its JSON."""

    builder = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False})
    if sequence_element:
        builder = builder.add(SequenceElement())
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


if __name__ == "__main__":
    unittest.main()

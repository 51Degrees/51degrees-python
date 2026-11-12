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

"""Evidence keys ignore letter case, as the Evidence page of the pipeline
specification says, so header.User-Agent and header.user-agent are the same
key. get_all gives each key in the letters it was added with, so an element
that matches a key it holds matches it in lower case."""

import json
import unittest
from unittest import mock

from fiftyone_pipeline_core import javascriptbuilder
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.sequenceelement import SequenceElement

from .classes.exampleflowelement1 import ExampleFlowElement1


def flowdata():
    return PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False}) \
        .add(ExampleFlowElement1()).build().create_flowdata()


class _Captured:
    """Records the variables of the last render and renders nothing."""

    def __init__(self):
        self.variables = None

    def render(self, template, variables):
        self.variables = dict(variables)
        return ""


def rendered_variables(evidence):
    """The variables the JavaScript Builder renders its script from, after a
    pipeline holding the Sequence Element has processed the evidence given."""

    pipeline = PipelineBuilder({"javascript_builder_settings": {
        "minify": False, "endpoint": "/json"}}).build()
    data = pipeline.create_flowdata()
    for key, value in evidence.items():
        data.evidence.add(key, value)
    captured = _Captured()
    with mock.patch.object(
            javascriptbuilder.chevron, "render", captured.render):
        data.process()
    return captured.variables


class EvidenceKeyCaseTests(unittest.TestCase):

    def test_a_key_is_read_in_any_case(self):
        data = flowdata()
        data.evidence.add("header.User-Agent", "a browser")
        self.assertEqual("a browser", data.evidence.get("header.user-agent"))
        self.assertEqual("a browser", data.evidence.get("HEADER.USER-AGENT"))

    def test_keys_that_differ_only_in_case_are_one_key(self):
        data = flowdata()
        data.evidence.add("header.User-Agent", "first")
        data.evidence.add("header.user-agent", "second")
        self.assertEqual(1, len(data.evidence.get_all()))
        self.assertEqual("second", data.evidence.get("header.User-Agent"))

    def test_a_key_in_any_case_survives_filtering(self):
        data = flowdata()
        data.evidence.add("Header.User-Agent", "a browser")
        data.process()
        self.assertEqual("a browser", data.evidence.get("header.user-agent"))

    def test_the_sequence_element_accepts_its_keys_in_any_case(self):
        """Without this the two keys move to the evidence set aside, and the
        Sequence Element then starts a session of its own."""

        data = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}) \
            .add(SequenceElement()).build().create_flowdata()
        data.evidence.add("Query.Session-Id", "abc-123")
        data.evidence.add("QUERY.SEQUENCE", "4")
        data.process()
        self.assertEqual({}, data.evidence.get_unaccepted())
        self.assertEqual("abc-123", data.evidence.get("query.session-id"))

    def test_the_script_takes_the_session_and_sequence_in_any_case(self):
        variables = rendered_variables({
            "Query.Session-Id": "abc-123", "QUERY.SEQUENCE": "4"})
        self.assertEqual("abc-123", variables["_sessionId"])
        # The Sequence Element counts this request as the next one.
        self.assertEqual(5, variables["_sequence"])

    def test_the_script_sends_a_query_value_whose_key_is_in_any_case(self):
        variables = rendered_variables({"Query.Example": "a value"})
        self.assertEqual(
            {"Example": "a+value"}, json.loads(variables["_parameters"]))


if __name__ == "__main__":
    unittest.main()

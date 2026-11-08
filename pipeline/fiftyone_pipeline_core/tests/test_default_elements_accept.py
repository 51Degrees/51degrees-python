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

"""The elements PipelineBuilder adds accept only the evidence they read, so
a default pipeline accepts what its engines read and no more. The ETag and
the Vary header of the client-side endpoints are built from what the
pipeline accepts."""

import unittest

from flask import Flask, request

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.javascriptbuilder import \
    JavascriptBuilderElement
from fiftyone_pipeline_core.jsonbundler import JSONBundlerElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.sequenceelement import SequenceElement
from fiftyone_pipeline_core.setheaderelement import SetHeaderElement

from .classes.exampleflowelement1 import ExampleFlowElement1


class DeclaresNothingElement(FlowElement):
    """An element that does not say which evidence it accepts."""

    def __init__(self):
        super(DeclaresNothingElement, self).__init__()
        self.datakey = "declaresnothing"

    def process_internal(self, flowdata):
        pass

NOT_READ = ("header.if-none-match", "header.x-test", "header.x-query",
            "header.cookie", "cookie.query", "server.client-ip")


def default_pipeline():
    """A pipeline with the elements the builder adds and one element that
    accepts header.user-agent alone."""
    return PipelineBuilder().add(ExampleFlowElement1()).build()


def accepted(pipeline, key):
    return any(element.filter_evidence_key(key)
               for element in pipeline.flow_elements)


class DefaultElementsAcceptTests(unittest.TestCase):

    def test_a_default_pipeline_accepts_only_what_its_elements_read(self):
        pipeline = default_pipeline()

        for key in NOT_READ:
            self.assertFalse(accepted(pipeline, key), key)
        for key in ("header.user-agent", "query.session-id",
                    "query.sequence", "query.fod-js-object-name",
                    "header.host", "header.protocol"):
            self.assertTrue(accepted(pipeline, key), key)

    def test_each_element_accepts_only_what_it_reads(self):
        sequence = SequenceElement()
        self.assertTrue(sequence.filter_evidence_key("query.session-id"))
        self.assertTrue(sequence.filter_evidence_key("query.sequence"))
        self.assertFalse(sequence.filter_evidence_key("query.other"))

        builder = JavascriptBuilderElement({})
        self.assertTrue(builder.filter_evidence_key("query.anything"))
        self.assertTrue(builder.filter_evidence_key("header.host"))
        self.assertTrue(builder.filter_evidence_key("header.protocol"))
        self.assertFalse(builder.filter_evidence_key("header.x-query"))
        self.assertFalse(builder.filter_evidence_key("cookie.query"))

        for element in (SetHeaderElement(), JSONBundlerElement()):
            for key in NOT_READ + ("header.user-agent", "query.sequence"):
                self.assertFalse(element.filter_evidence_key(key),
                                 type(element).__name__ + " " + key)

    def test_processing_sets_aside_the_evidence_no_element_reads(self):
        flowdata = default_pipeline().create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("header.if-none-match", '"a-tag"')
        flowdata.process()

        self.assertEqual("a browser",
                         flowdata.evidence.get("header.user-agent"))
        self.assertIsNone(flowdata.evidence.get("header.if-none-match"))

    def test_only_the_headers_the_elements_read_are_named_for_vary(self):
        """The client-side endpoints name in Vary the request headers the
        pipeline accepts."""

        pipeline = default_pipeline()
        with Flask(__name__).test_request_context("/", headers={
                "User-Agent": "a browser", "Accept": "*/*",
                "Accept-Language": "en", "Cookie": "a=b",
                "If-None-Match": '"a-tag"', "X-Test": "x"}):
            named = sorted(name for name, _ in request.headers
                           if accepted(pipeline, "header." + name.lower()))

        self.assertEqual(["Host", "User-Agent"], named)


    def test_an_element_that_declares_nothing_accepts_nothing(self):
        element = DeclaresNothingElement()
        for key in NOT_READ + ("header.user-agent", "query.session-id"):
            self.assertFalse(element.filter_evidence_key(key), key)

    def test_an_element_that_declares_nothing_widens_nothing(self):
        pipeline = PipelineBuilder() \
            .add(ExampleFlowElement1()) \
            .add(DeclaresNothingElement()) \
            .build()
        for key in NOT_READ:
            self.assertFalse(accepted(pipeline, key), key)
        self.assertTrue(accepted(pipeline, "header.user-agent"))


if __name__ == "__main__":
    unittest.main()

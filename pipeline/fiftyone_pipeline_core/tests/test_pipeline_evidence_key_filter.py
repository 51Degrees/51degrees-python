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
from unittest import mock

from fiftyone_pipeline_core import pipeline as pipeline_module
from fiftyone_pipeline_core import web
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}


class Element(FlowElement):
    """An element that accepts the keys it holds when asked."""

    def __init__(self, datakey, keys):
        super(Element, self).__init__()
        self.datakey = datakey
        self.keys = keys

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(self.keys)

    def process_internal(self, flowdata):
        pass


class NotReady(Exception):
    """Raised by an element that cannot yet say what it accepts."""


class Recovering(FlowElement):
    """An element that cannot say what it accepts until it has recovered,
    as an element that learns its keys from a service does while the
    service cannot be reached."""

    def __init__(self):
        super(Recovering, self).__init__()
        self.datakey = "recovering"
        self.recovered = False

    def get_evidence_key_filter(self):
        if not self.recovered:
            raise NotReady("The stand-in service cannot be reached.")
        return BasicListEvidenceKeyFilter(["header.x-recovered"])

    def process_internal(self, flowdata):
        pass


class FiltersWhenRegistered(FlowElement):
    """An element that filters a FlowData's evidence as soon as it is
    registered, before the Pipeline's constructor has finished."""

    def __init__(self):
        super(FiltersWhenRegistered, self).__init__()
        self.datakey = "early"
        self.kept = None
        self.set_aside = None

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["header.user-agent"])

    def on_registration(self, pipeline):
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("cookie.other", "not read")
        flowdata.evidence.filter()
        self.kept = dict(flowdata.evidence.get_all())
        self.set_aside = dict(flowdata.evidence.get_unaccepted())

    def process_internal(self, flowdata):
        pass


class PipelineEvidenceKeyFilterTests(unittest.TestCase):
    """!
    advertize-accepted-evidence.md line 5: "All Flow Elements and Pipelines
    MUST be capable of programmatically describing the Evidence keys that
    they can make use of."
    """

    def build(self, *elements):
        builder = PipelineBuilder(NO_DEFAULT_ELEMENTS)
        for element in elements:
            builder.add(element)
        pipeline = builder.build()
        self.addCleanup(pipeline.close)
        return pipeline

    def test_the_pipeline_accepts_what_any_element_accepts(self):
        accepted = self.build(
            Element("one", ["header.user-agent"]),
            Element("two", ["query.mark"])).get_evidence_key_filter()
        self.assertTrue(accepted.filter_evidence_key("header.user-agent"))
        self.assertTrue(accepted.filter_evidence_key("Header.User-Agent"))
        self.assertTrue(accepted.filter_evidence_key("query.mark"))
        self.assertFalse(accepted.filter_evidence_key("cookie.other"))

    def test_the_pipeline_reads_its_elements_filters_when_asked(self):
        later = Element("later", [])
        accepted = self.build(later).get_evidence_key_filter()
        self.assertFalse(accepted.filter_evidence_key("header.x-later"))
        later.keys = ["header.x-later"]
        self.assertTrue(accepted.filter_evidence_key("header.x-later"))

    def test_the_pipeline_gives_the_same_filter_every_time(self):
        pipeline = self.build(Element("one", ["header.user-agent"]))
        self.assertIs(
            pipeline.get_evidence_key_filter(),
            pipeline.get_evidence_key_filter())

    def test_the_pipeline_builds_its_filter_once_when_it_is_created(self):
        # The Pipeline's filter is always needed and does not change, so it
        # is built in the constructor and not on each call.
        real = pipeline_module.PipelineEvidenceKeyFilter
        with mock.patch.object(
                pipeline_module, "PipelineEvidenceKeyFilter",
                side_effect=real) as made:
            pipeline = self.build(Element("one", ["header.user-agent"]))
            self.assertEqual(1, made.call_count)
            first = pipeline.get_evidence_key_filter()
            pipeline.get_evidence_key_filter()
            self.assertEqual(1, made.call_count)
        self.assertIsInstance(first, real)
        self.assertTrue(first.filter_evidence_key("header.user-agent"))

    def test_the_pipeline_filters_evidence_to_what_it_accepts(self):
        pipeline = self.build(Element("one", ["header.user-agent"]))
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("cookie.other", "not read")
        self.assertEqual(
            {"header.user-agent": "a browser"},
            pipeline.get_evidence_key_filter().filter_evidence(
                flowdata.evidence.get_all()))

    def test_processing_filters_evidence_with_the_pipelines_filter(self):
        # The filter built with the Pipeline is the one processing uses, so
        # there is one place that decides what the Pipeline accepts.
        pipeline = self.build(Element("one", ["header.user-agent"]))
        accepted = pipeline.get_evidence_key_filter()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("cookie.other", "not read")
        with mock.patch.object(
                accepted, "filter_evidence_key",
                wraps=accepted.filter_evidence_key) as asked:
            flowdata.process()
        self.assertEqual(
            [mock.call("header.user-agent"), mock.call("cookie.other")],
            asked.call_args_list)
        self.assertEqual(
            {"header.user-agent": "a browser"}, flowdata.evidence.get_all())
        self.assertEqual(
            {"cookie.other": "not read"}, flowdata.evidence.get_unaccepted())

    def test_processing_follows_an_element_whose_keys_arrive_later(self):
        # Processing reads the Pipeline's filter, and that filter asks each
        # element at the time, so keys an element gains after the Pipeline
        # is built are kept.
        later = Element("later", [])
        pipeline = self.build(later)
        accepted = pipeline.get_evidence_key_filter()
        later.keys = ["header.x-later"]
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.x-later", "kept")
        with mock.patch.object(
                accepted, "filter_evidence_key",
                wraps=accepted.filter_evidence_key) as asked:
            flowdata.process()
        self.assertEqual(
            [mock.call("header.x-later")], asked.call_args_list)
        self.assertEqual(
            {"header.x-later": "kept"}, flowdata.evidence.get_all())

    def test_the_web_integration_asks_the_pipelines_filter(self):
        # The entity tag and the Vary header of the client-side responses
        # are made from the evidence the Pipeline accepts.
        pipeline = self.build(Element("one", ["header.user-agent"]))
        accepted = pipeline.get_evidence_key_filter()
        with mock.patch.object(
                accepted, "filter_evidence_key",
                wraps=accepted.filter_evidence_key) as asked:
            self.assertTrue(web._uses(pipeline, "header.user-agent"))
            self.assertFalse(web._uses(pipeline, "cookie.other"))
            # Neither of these is evidence an element uses, whatever the
            # filters accept, so the filter is not asked about them.
            self.assertFalse(web._uses(pipeline, "server.http-request"))
            self.assertFalse(web._uses(pipeline, "header.if-none-match"))
        self.assertEqual(
            [mock.call("header.user-agent"), mock.call("cookie.other")],
            asked.call_args_list)

    def test_the_pipeline_is_built_while_an_element_cannot_answer(self):
        # Building the Pipeline asks no element for its filter, so an
        # element that cannot answer yet does not stop the build. The
        # element is asked each time a key is checked, and nothing is kept
        # from before it could answer.
        recovering = Recovering()
        pipeline = self.build(
            Element("one", ["header.user-agent"]), recovering)
        accepted = pipeline.get_evidence_key_filter()
        with self.assertRaises(NotReady):
            accepted.filter_evidence_key("header.x-recovered")
        recovering.recovered = True
        self.assertTrue(accepted.filter_evidence_key("header.x-recovered"))
        self.assertTrue(accepted.filter_evidence_key("header.user-agent"))
        self.assertFalse(accepted.filter_evidence_key("cookie.other"))
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.x-recovered", "kept")
        flowdata.evidence.add("cookie.other", "not read")
        flowdata.process()
        self.assertEqual(
            {"header.x-recovered": "kept"}, flowdata.evidence.get_all())

    def test_evidence_is_filtered_while_the_pipeline_is_being_built(self):
        # An element may use the Pipeline as soon as it is registered, so
        # the filter is there before the first element is.
        early = FiltersWhenRegistered()
        self.build(early)
        self.assertEqual({"header.user-agent": "a browser"}, early.kept)
        self.assertEqual({"cookie.other": "not read"}, early.set_aside)


if __name__ == "__main__":
    unittest.main()

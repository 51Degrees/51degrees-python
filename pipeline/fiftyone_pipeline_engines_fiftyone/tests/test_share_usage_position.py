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
The usage sharing element is the last Flow Element of every Pipeline the
builder makes, and a Pipeline that puts it anywhere else is refused, whether
it is built in code or from a configuration. Python has no parallel groups,
so the element is always outside one.
"""

import gzip
import re
import unittest
from unittest import mock

import requests

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

# The package size is never reached, so the element sends nothing until it
# is closed.
QUEUE_ONLY = {
    "requested_package_size": 1000,
    "endpoint": "http://127.0.0.1:9",
}

REFUSED = (
    "The usage sharing element must be the last Flow Element and outside "
    "any parallel group.")

USAGE_SHARING = {
    "elementName": "ShareUsage",
    "elementPath": "fiftyone_pipeline_engines_fiftyone.share_usage",
    "elementParameters": QUEUE_ONLY,
}

SEQUENCE = {
    "elementName": "SequenceElement",
    "elementPath": "fiftyone_pipeline_core.sequenceelement",
}


class AddsEvidence(FlowElement):
    """Adds a header to the Evidence as it processes."""

    def __init__(self):
        super(AddsEvidence, self).__init__()
        self.datakey = "addsevidence"

    def process_internal(self, flowdata):
        flowdata.evidence.add("header.x-added", "added value")


def configuration(*elements):
    return {"PipelineOptions": {"Elements": list(elements)}}


def sent_on_close(usage):
    """Closes the element, which sends what it has queued, and returns each
    record it posted. The post is answered without leaving the process."""
    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


class UsageSharingLastTests(unittest.TestCase):

    def usage(self):
        usage = ShareUsage(**QUEUE_ONLY)
        self.addCleanup(usage.close)
        return usage

    def test_builder_puts_it_after_the_web_integration_elements(self):
        usage = self.usage()
        pipeline = PipelineBuilder().add(AddsEvidence()).add(usage).build()

        self.assertEqual(
            ["sequence", "addsevidence", "jsonbundler", "javascriptbuilder",
             "set-headers", "shareusage"],
            [element.datakey for element in pipeline.flow_elements])

    def test_configuration_with_it_last_builds(self):
        pipeline = PipelineBuilder().build_from_configuration(
            configuration(SEQUENCE, USAGE_SHARING))
        self.addCleanup(pipeline.close)

        self.assertIsInstance(pipeline.flow_elements[-1], ShareUsage)

    def test_it_shares_evidence_an_earlier_element_adds(self):
        usage = ShareUsage(**QUEUE_ONLY)
        pipeline = PipelineBuilder().add(AddsEvidence()).add(usage).build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "agent value")
        flowdata.process()

        records = sent_on_close(usage)

        self.assertEqual(1, len(records))
        self.assertIn('<header Name="x-added">added value</header>',
                      records[0])


class UsageSharingElsewhereIsRefusedTests(unittest.TestCase):

    def usage(self):
        usage = ShareUsage(**QUEUE_ONLY)
        self.addCleanup(usage.close)
        return usage

    def test_builder_refuses_it_first(self):
        builder = PipelineBuilder().add(self.usage()).add(AddsEvidence())

        with self.assertRaisesRegex(ValueError, re.escape(REFUSED)):
            builder.build()

    def test_builder_refuses_it_first_without_web_elements(self):
        builder = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False,
        }).add(self.usage()).add(AddsEvidence())

        with self.assertRaisesRegex(ValueError, re.escape(REFUSED)):
            builder.build()

    def test_builder_refuses_a_second_one(self):
        builder = PipelineBuilder().add(self.usage()).add(self.usage())

        with self.assertRaisesRegex(ValueError, re.escape(REFUSED)):
            builder.build()

    def test_configuration_refuses_it_first(self):
        with self.assertRaisesRegex(ValueError, re.escape(REFUSED)):
            PipelineBuilder().build_from_configuration(
                configuration(USAGE_SHARING, SEQUENCE))

    def test_pipeline_refuses_it_first(self):
        with self.assertRaisesRegex(ValueError, re.escape(REFUSED)):
            Pipeline([self.usage(), AddsEvidence()])

    def test_refused_element_is_not_registered(self):
        usage = self.usage()

        with self.assertRaises(ValueError):
            Pipeline([usage, AddsEvidence()])

        self.assertEqual([], usage.pipelines)

    def test_error_names_the_element_and_its_position(self):
        with self.assertRaisesRegex(
                ValueError, "ShareUsage is Flow Element 1 of 2"):
            Pipeline([self.usage(), AddsEvidence()])


if __name__ == "__main__":
    unittest.main()

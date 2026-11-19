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
One usage sharing element in two Pipelines. A record that carries the
invariant values names the flow elements of the Pipeline its request came
from, as multi-pipeline-elements.md asks of an element that keeps state for
a Pipeline. The element writes those values to the first record it writes,
whichever Pipeline that is from, and keeps one hour for every Pipeline.
"""

import gzip
import re
import unittest
from unittest import mock

import requests

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

HOUR = 3600

INVARIANT_ELEMENTS = (
    "Version", "Product", "FlowElement", "Package", "Language",
    "LanguageVersion", "ServerIP", "Platform",
)


class Clock:
    """A clock the test moves by hand, in seconds."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FirstElement(FlowElement):

    def __init__(self):
        super(FirstElement, self).__init__()
        self.datakey = "first"

    def process_internal(self, flowdata):
        pass


class SecondElement(FlowElement):

    def __init__(self):
        super(SecondElement, self).__init__()
        self.datakey = "second"

    def process_internal(self, flowdata):
        pass


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


def process(pipeline, user_agent):
    with pipeline.create_flowdata() as flowdata:
        flowdata.evidence.add("header.user-agent", user_agent)
        flowdata.process()


def flow_elements_in(record):
    return re.findall(r"<FlowElement>([^<]*)</FlowElement>", record)


def invariants_in(record):
    """The names of the invariant elements a record carries."""
    return [name for name in INVARIANT_ELEMENTS
            if re.search("<" + name + r"[ >]", record)]


def element_in_two_pipelines():
    """One usage sharing element added to two Pipelines, with a clock the
    test moves. It waits until the lookup of the server's address has
    ended, as a record written before then does not count as carrying the
    invariant values."""
    usage = ShareUsage(requested_package_size=1000,
                       endpoint="http://127.0.0.1:9")
    usage._server_ip_found.wait(10)
    clock = Clock()
    usage.clock = clock
    first = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
        .add(FirstElement()).add(usage).build()
    second = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
        .add(SecondElement()).add(usage).build()
    return usage, clock, first, second


class ShareUsagePipelinesTests(unittest.TestCase):

    def test_each_record_names_the_elements_of_its_own_pipeline(self):
        # The flow elements are invariant values, so only a record that
        # carries them names them. The second request comes an hour after
        # the first, so that its record carries them too.
        usage, clock, first, second = element_in_two_pipelines()

        process(first, "first agent")
        clock.now += HOUR
        process(second, "second agent")
        records = sent_on_close(usage)

        self.assertEqual(
            [["FirstElement", "ShareUsage"], ["SecondElement", "ShareUsage"]],
            [flow_elements_in(record) for record in records])

    def test_only_the_first_record_the_element_writes_carries_them(self):
        # usage-sharing-element.md lines 203 to 209 at d79bbe3b: "The
        # invariant values MUST be written to the first record the element
        # writes" and "They MUST NOT be written to any other record". The
        # first record from the second Pipeline is not the first record
        # the element writes.
        usage, clock, first, second = element_in_two_pipelines()

        for index in range(2):
            process(first, f"first agent {index}")
            clock.now += 1
            process(second, f"second agent {index}")
            clock.now += 1
        records = sent_on_close(usage)

        self.assertEqual(4, len(records))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[0]))
        self.assertEqual(["FirstElement", "ShareUsage"],
                         flow_elements_in(records[0]))
        for record in records[1:]:
            self.assertEqual([], invariants_in(record))

    def test_the_element_keeps_one_hour_for_every_pipeline(self):
        # Lines 204 and 205: "They MUST be written again to the first
        # record the element writes once an hour or more has passed since
        # it last wrote them", from whichever Pipeline that record is.
        usage, clock, first, second = element_in_two_pipelines()

        process(first, "first")
        clock.now += HOUR / 2
        process(second, "half an hour later")
        clock.now += HOUR / 2
        process(second, "an hour after the first")
        clock.now += HOUR / 2
        process(first, "half an hour after that")
        records = sent_on_close(usage)

        self.assertEqual(
            [["FirstElement", "ShareUsage"], [],
             ["SecondElement", "ShareUsage"], []],
            [flow_elements_in(record) for record in records])
        self.assertEqual([], invariants_in(records[1]))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[2]))
        self.assertEqual([], invariants_in(records[3]))


if __name__ == "__main__":
    unittest.main()

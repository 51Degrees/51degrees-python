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
One usage sharing element in two Pipelines. Each record names the flow
elements of the Pipeline its request came from, as
multi-pipeline-elements.md asks of an element that keeps state for a
Pipeline.
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


class ShareUsagePipelinesTests(unittest.TestCase):

    def test_each_record_names_the_elements_of_its_own_pipeline(self):
        usage = ShareUsage(requested_package_size=1000,
                           endpoint="http://127.0.0.1:9")
        first = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add(FirstElement()).add(usage).build()
        second = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add(SecondElement()).add(usage).build()

        for _ in range(2):
            process(first, "first agent")
            process(second, "second agent")
        records = sent_on_close(usage)

        by_agent = {}
        for record in records:
            agent = re.search(r'Name="user-agent">([^<]*)<', record).group(1)
            by_agent.setdefault(agent, []).append(
                re.findall(r"<FlowElement>([^<]*)</FlowElement>", record))
        self.assertEqual(
            {"first agent": [["FirstElement", "ShareUsage"]],
             "second agent": [["SecondElement", "ShareUsage"]]},
            by_agent)


if __name__ == "__main__":
    unittest.main()

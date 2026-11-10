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
key."""

import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.exampleflowelement1 import ExampleFlowElement1


def flowdata():
    return PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False}) \
        .add(ExampleFlowElement1()).build().create_flowdata()


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


if __name__ == "__main__":
    unittest.main()

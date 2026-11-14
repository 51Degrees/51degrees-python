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

    def test_the_pipeline_filters_evidence_to_what_it_accepts(self):
        pipeline = self.build(Element("one", ["header.user-agent"]))
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("cookie.other", "not read")
        self.assertEqual(
            {"header.user-agent": "a browser"},
            pipeline.get_evidence_key_filter().filter_evidence(
                flowdata.evidence.get_all()))


if __name__ == "__main__":
    unittest.main()

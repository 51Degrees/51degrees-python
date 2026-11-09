
"""
Evidence whose key strips to values, resource, license or licence, in any
letter case, is left out of the request, as the Cloud Request Engine
specification says.
"""

import warnings

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase


class TestReservedEvidence(CloudRequestEngineTestsBase):

    def content_for(self, evidence):
        engine = CloudRequestEngine({
            "resource_key": "resource_key", "http_client": self.mock_http()})
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}).add(engine).build()
        self.addCleanup(pipeline.close)
        data = pipeline.create_flowdata()
        for key, value in evidence.items():
            data.evidence.add(key, value)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            content = engine.get_content(data)
        return content, caught

    def test_each_reserved_name_is_left_out_in_any_letter_case(self):
        for name in ("values", "Values", "resource", "RESOURCE", "license",
                     "License", "licence", "Licence", "LICENCE"):
            for prefix in ("query.", "header.", "cookie."):
                content, caught = self.content_for(
                    {prefix + name: "secret", "header.user-agent": "iPhone"})
                self.assertEqual(
                    {"user-agent": "iPhone"}, content, prefix + name)
                self.assertEqual(1, len(caught), prefix + name)
                self.assertNotIn("secret", str(caught[0].message))

    def test_other_evidence_is_kept(self):
        content, caught = self.content_for(
            {"query.sequence": 1, "header.user-agent": "iPhone"})
        self.assertEqual({"sequence": 1, "user-agent": "iPhone"}, content)
        self.assertEqual([], caught)

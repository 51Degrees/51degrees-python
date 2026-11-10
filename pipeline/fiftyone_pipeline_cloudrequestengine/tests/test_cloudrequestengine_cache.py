
"""
A cache never stores or serves a Cloud Request Engine response that holds a
value created for one request, being a top-level member named fodid in any
case, as the caching page of the specification says.
"""

import json

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.basic_dictionary_cache import \
    BasicDictionaryCache

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.mockrequestclient import MockRequestClient


class CountingClient(MockRequestClient):
    """Answers every data request with the same text and counts them."""

    def __init__(self, answer):
        super(CountingClient, self).__init__()
        self.answer = answer
        self.data_requests = 0

    def request(self, type, url, content, originHeader):
        response = super(CountingClient, self).request(
            type, url, content, originHeader)
        if "resource_key.json" in url:
            self.data_requests += 1
            response.text = self.answer
        return response


class TestCloudRequestEngineCache(CloudRequestEngineTestsBase):

    def requests_for(self, answer):
        """Two requests with the same evidence, through a cache. Gives how
        many reached the cloud service."""

        client = CountingClient(answer)
        engine = CloudRequestEngine({
            "resource_key": "resource_key", "http_client": client})
        engine.set_cache(BasicDictionaryCache())
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}).add(engine).build()
        self.addCleanup(pipeline.close)
        for _ in range(2):
            data = pipeline.create_flowdata()
            data.evidence.add("query.User-Agent", "iPhone")
            data.process()
            self.assertEqual(answer, data.get("cloud").get("cloud"))
        return client.data_requests

    def test_an_ordinary_response_is_cached(self):
        answer = json.dumps({"device": {"ismobile": True}})
        self.assertEqual(1, self.requests_for(answer))

    def test_a_response_with_a_fodid_is_neither_stored_nor_served(self):
        for name in ("fodid", "FodId", "FODID"):
            answer = json.dumps({"device": {"ismobile": True}, name: "abc"})
            self.assertEqual(2, self.requests_for(answer), name)

    def test_a_fodid_below_the_top_level_does_not_count(self):
        answer = json.dumps({"device": {"fodid": "abc"}})
        self.assertEqual(1, self.requests_for(answer))

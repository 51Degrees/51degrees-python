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
A cache never stores or serves a Cloud Request Engine response that holds a
value created for one request, being a top-level member named fodid in any
case, as the caching page of the specification says.
"""

import json

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.aspectdata_dictionary import \
    AspectDataDictionary
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


class AlwaysHitCache(BasicDictionaryCache):
    """Answers every lookup with the one entry it holds, so that a reader
    reaches an entry the engine never stored itself."""

    def __init__(self):
        super(AlwaysHitCache, self).__init__()
        self.entry = None

    def get_cache_value(self, key):
        return self.entry


class TestCloudRequestEngineCache(CloudRequestEngineTestsBase):

    def pipeline_for(self, client, cache):
        """A pipeline holding one Cloud Request Engine with the cache given.
        Gives the engine and the pipeline."""

        engine = CloudRequestEngine({
            "resource_key": "resource_key", "http_client": client})
        engine.set_cache(cache)
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}).add(engine).build()
        self.addCleanup(pipeline.close)
        return engine, pipeline

    def answer_for(self, pipeline):
        """One request through the pipeline. Gives the response text the
        request ended with."""

        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", "iPhone")
        data.process()
        return data.get("cloud").get("cloud")

    def requests_for(self, answer):
        """Two requests with the same evidence, through a cache. Gives how
        many reached the cloud service."""

        client = CountingClient(answer)
        _, pipeline = self.pipeline_for(client, BasicDictionaryCache())
        for _ in range(2):
            self.assertEqual(answer, self.answer_for(pipeline))
        return client.data_requests

    def found_in_cache(self, entry_text):
        """One request whose cache answers with an entry holding entry_text,
        where the cloud service answers with something else. Gives the
        response text the request ended with and how many requests reached
        the service."""

        answer = json.dumps({"device": {"ismobile": False}})
        client = CountingClient(answer)
        cache = AlwaysHitCache()
        engine, pipeline = self.pipeline_for(client, cache)
        cache.entry = AspectDataDictionary(engine, {"cloud": entry_text})
        return self.answer_for(pipeline), client.data_requests

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

    def test_an_entry_without_a_fodid_is_served(self):
        """The cache really is read, so the test below says something."""

        entry_text = json.dumps({"device": {"ismobile": True}})
        served, requests = self.found_in_cache(entry_text)
        self.assertEqual(entry_text, served)
        self.assertEqual(0, requests)

    def test_an_entry_holding_a_fodid_is_not_served(self):
        for name in ("fodid", "FodId", "FODID"):
            entry_text = json.dumps({"device": {"ismobile": True},
                                     name: "abc"})
            served, requests = self.found_in_cache(entry_text)
            self.assertNotEqual(entry_text, served, name)
            self.assertEqual(1, requests, name)

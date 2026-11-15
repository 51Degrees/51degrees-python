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
import json

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

from fiftyone_pipeline_engines.engine import Engine
from fiftyone_pipeline_engines.datakeyed_cache import DataKeyedCache
from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary

from fiftyone_pipeline_engines.lru_cache import LRUEngineCache

class TestCache(DataKeyedCache):
    
    def __init__(self):

        self.cache = {}
        self.cacheHits = 0

    def get_cache_value(self, key):
        if key in self.cache:
            self.cacheHits += 1
            return self.cache[key]
        else:
            return None

    def set_cache_value(self, key, value):
        self.cache[key] = value

class ExampleAspectEngine(Engine):

    def __init__(self):

        super(ExampleAspectEngine, self).__init__()

        self.datakey = "example"

        self.properties = {
            "integer": {
                "type" : "int"
            },
            "boolean": {
                "type" : "bool"
            }
        }

    def get_evidence_key_filter(self):

        return BasicListEvidenceKeyFilter(["header.test"])
        
    def process_internal(self, flowdata):

        data = AspectDataDictionary(self, {"integer" : 5, "boolean" : True})

        flowdata.set_element_data(data)

class CountingEngine(Engine):

    """!
    An engine that counts its calls to process_internal, so a test can see
    whether a result came from the cache.
    """

    def __init__(self):

        super(CountingEngine, self).__init__()

        self.datakey = "counting"

        self.properties = {"call": {"type": "int"}}

        self.calls = 0

    def get_evidence_key_filter(self):

        return BasicListEvidenceKeyFilter(
            ["header.a", "header.b", "query.user-agent"])

    def process_internal(self, flowdata):

        self.calls += 1

        flowdata.set_element_data(
            AspectDataDictionary(self, {"call": self.calls}))

class EngineTests(unittest.TestCase):

    # Test Engine processing
    def testEngineProcessing(self):
    
        testPipeline = PipelineBuilder().add(ExampleAspectEngine()).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.process()

        self.assertTrue(flowdata.example.integer == 5)

    # Test restricting properties
    def testRestrictedProperty(self):
        
        engine = ExampleAspectEngine()

        engine.set_restricted_properties(["boolean"])

        testPipeline = PipelineBuilder().add(engine).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.process()

        try:
            flowdata.example.get("integer")
        except Exception as e:
            result = str(e)

        self.assertEqual(
            "Property 'integer' not found in data for element 'example'. "
            "This is because the property has been excluded when configuring "
            "the engine.", result)

    # Restricted property names are compared ignoring case
    def testRestrictedPropertyIgnoresCase(self):

        engine = ExampleAspectEngine()

        engine.set_restricted_properties(["Boolean"])

        testPipeline = PipelineBuilder().add(engine).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.process()

        # A name given in another case is in the list.
        self.assertTrue(flowdata.example.get("boolean"))
        self.assertTrue(flowdata.example.boolean)

        # A name outside the list is refused in any case.
        for key in ("integer", "Integer"):
            with self.assertRaises(Exception) as refused:
                flowdata.example.get(key)
            self.assertEqual(
                "Property '" + key + "' not found in data for element "
                "'example'. This is because the property has been excluded "
                "when configuring the engine.",
                str(refused.exception))

    # Test restricting properties
    def testMissingPropertyService(self):
        
        engine = ExampleAspectEngine()

        testPipeline = PipelineBuilder().add(engine).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.process()

        try:
           flowdata.example.get("missing")
        except Exception as e:
            result = str(e)

        self.assertEqual(
            "Property 'missing' not found in data for element 'example'. "
            "The reason for this is unknown. Please check that the aspect and "
            "property name are correct.", result)

    # Test cache
    
    def testCache(self):
        
        engine = ExampleAspectEngine()

        cache = TestCache()

        engine.set_cache(cache)

        testPipeline = PipelineBuilder().add(engine).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.evidence.add("header.test", "test")

        flowdata.process()

        flowdata2 = testPipeline.create_flowdata()

        flowdata2.evidence.add("header.test", "test")

        flowdata2.process()

        self.assertEqual(cache.cacheHits, 1)

    def testLRUCache(self):

        engine = ExampleAspectEngine()

        cache = LRUEngineCache()

        engine.set_cache(cache)

        testPipeline = PipelineBuilder().add(engine).build()

        flowdata = testPipeline.create_flowdata()

        flowdata.evidence.add("header.test", "test")

        flowdata.process()

        flowdata2 = testPipeline.create_flowdata()

        flowdata2.evidence.add("header.test", "test")

        flowdata2.process()

        self.assertEqual(cache.cache.currsize, 1)

    def results_for(self, *requests):

        """!
        Processes one FlowData for each request through one CountingEngine
        with a cache. A request is a list of evidence keys and values, added
        in the order given. Gives the engine and each request's result.
        """

        engine = CountingEngine()

        engine.set_cache(TestCache())

        pipeline = PipelineBuilder().add(engine).build()

        results = []

        for request in requests:
            flowdata = pipeline.create_flowdata()
            for key, value in request:
                flowdata.evidence.add(key, value)
            flowdata.process()
            results.append(flowdata.get("counting"))

        return engine, results

    # The same evidence added in another order is the same cache key.
    def testCacheKeyIgnoresEvidenceOrder(self):

        engine, results = self.results_for(
            [("header.a", "1"), ("header.b", "2")],
            [("header.b", "2"), ("header.a", "1")])

        self.assertEqual(1, engine.calls)
        self.assertIs(results[0], results[1])
        self.assertEqual(1, results[1].get("call"))

    # Evidence keys that differ only in letter case are the same cache key.
    def testCacheKeyIgnoresKeyCase(self):

        engine, results = self.results_for(
            [("query.User-Agent", "abc"), ("Header.A", "1")],
            [("query.user-agent", "abc"), ("header.a", "1")])

        self.assertEqual(1, engine.calls)
        self.assertIs(results[0], results[1])
        self.assertEqual(1, results[1].get("call"))

    # Evidence values are compared with their letter case, so different
    # values, including ones that differ only in case, are processed again.
    def testCacheKeyKeepsEvidenceValues(self):

        for first, second in (("abc", "xyz"), ("abc", "ABC")):
            with self.subTest(second=second):

                engine, results = self.results_for(
                    [("query.user-agent", first)],
                    [("query.user-agent", second)])

                self.assertEqual(2, engine.calls)
                self.assertIsNot(results[0], results[1])
                self.assertEqual(2, results[1].get("call"))

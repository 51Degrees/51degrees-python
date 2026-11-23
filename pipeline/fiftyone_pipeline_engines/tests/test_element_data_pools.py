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
An instance a cache holds never goes back to a pool, because the cache
shares it with other requests, as the resource cleanup page of the
specification requires.
"""

import unittest

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.datakeyed_cache import DataKeyedCache
from fiftyone_pipeline_engines.engine import Engine


class DictionaryCache(DataKeyedCache):

    def __init__(self):
        self.entries = {}

    def get_cache_value(self, key):
        return self.entries.get(key)

    def set_cache_value(self, key, value):
        self.entries[key] = value


class PooledEngine(Engine):
    """Takes its ElementData from a pool and writes the query name into
    it."""

    def __init__(self):
        from fiftyone_pipeline_core.elementdata_pool import ElementDataPool
        super(PooledEngine, self).__init__()
        self.datakey = "pooled"
        self.properties = {"name": {"type": "string"}}
        self._element_data_pool = ElementDataPool()

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["query.name"])

    def process_internal(self, flowdata):
        data = self._element_data_pool.take()
        if data is None:
            data = ElementDataDictionary(self, {})
        data.contents["name"] = flowdata.evidence.get("query.name")
        flowdata.set_element_data(data)


def process(pipeline, name):
    flowdata = pipeline.create_flowdata()
    flowdata.evidence.add("query.name", name)
    flowdata.process()
    return flowdata


class CachedElementDataTests(unittest.TestCase):

    def test_an_instance_held_by_a_cache_is_never_reused(self):
        engine = PooledEngine()
        engine.set_cache(DictionaryCache())
        pipeline = PipelineBuilder({"add_javascript_builder": False,
                                    "use_setheader_properties": False}) \
            .add(engine).build()
        with process(pipeline, "first") as flowdata:
            cached = flowdata.pooled
        with process(pipeline, "first") as flowdata:
            self.assertIs(cached, flowdata.pooled)
        with process(pipeline, "second") as flowdata:
            self.assertIsNot(cached, flowdata.pooled)
            self.assertEqual("second", flowdata.pooled.get("name"))
        self.assertEqual("first", cached.get("name"))
        self.assertEqual(0, len(engine._element_data_pool))

    def test_an_engine_without_a_cache_reuses_its_instance(self):
        engine = PooledEngine()
        pipeline = PipelineBuilder({"add_javascript_builder": False,
                                    "use_setheader_properties": False}) \
            .add(engine).build()
        with process(pipeline, "first") as flowdata:
            first = flowdata.pooled
        with process(pipeline, "second") as flowdata:
            self.assertIs(first, flowdata.pooled)
            self.assertEqual("second", flowdata.pooled.get("name"))


if __name__ == "__main__":
    unittest.main()

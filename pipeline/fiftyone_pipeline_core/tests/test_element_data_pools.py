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
ElementData comes from a bounded pool for each FlowElement that keeps one,
and closing a FlowData gives its ElementData back, as the resource cleanup
page of the specification describes. Over many requests the instances made
stay at the pool's bound rather than one for each request. A reused
instance starts with no values and open for writing, and the instances of a
FlowData that is not closed are left to the garbage collector.
"""

import gc
import threading
import unittest
import weakref
from unittest import mock

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.sequenceelement import SequenceElement

# Far more requests than any pool's bound.
REQUESTS = 200

# A small bound, so that a test can hold more FlowData open than it.
BOUND = 4

# The threads that process requests at once in the threaded test.
THREADS = 4

FINISHED = "finished processing"


def count_constructions(test, cls):
    """Counts each instance of cls made until the test ends, keyed by the
    data key of the FlowElement that made it."""
    counts = {}
    original = cls.__init__

    def counting(self, flow_element, *args, **kwargs):
        key = flow_element.datakey
        counts[key] = counts.get(key, 0) + 1
        original(self, flow_element, *args, **kwargs)

    patcher = mock.patch.object(cls, "__init__", counting)
    patcher.start()
    test.addCleanup(patcher.stop)
    return counts


class PooledElement(FlowElement):
    """Takes its ElementData from a pool and writes the query name and
    value into it, as contents and as a public attribute, which only an
    instance open for writing takes."""

    def __init__(self, bound=BOUND):
        from fiftyone_pipeline_core.elementdata_pool import ElementDataPool
        super(PooledElement, self).__init__()
        self.datakey = "pooled"
        self._element_data_pool = ElementDataPool(bound)

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["query.name", "query.value"])

    def process_internal(self, flowdata):
        data = self._element_data_pool.take()
        if data is None:
            data = ElementDataDictionary(self, {})
        name = flowdata.evidence.get("query.name")
        data.contents[name] = flowdata.evidence.get("query.value")
        data.last_name = name
        flowdata.set_element_data(data)


class OwnAttributeElement(FlowElement):
    """Keeps no pool, but has an attribute of its own with the name the
    pooled elements use, holding something else."""

    def __init__(self):
        super(OwnAttributeElement, self).__init__()
        self.datakey = "own"
        self._element_data_pool = "a value of the element's own"

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {"a": 1}))


def build(*elements):
    builder = PipelineBuilder({"add_javascript_builder": False,
                               "use_setheader_properties": False})
    for element in elements:
        builder.add(element)
    return builder.build()


def process(pipeline, name="name", value="value"):
    flowdata = pipeline.create_flowdata()
    flowdata.evidence.add("header.user-agent", "a user agent")
    flowdata.evidence.add("query.name", name)
    flowdata.evidence.add("query.value", value)
    flowdata.process()
    return flowdata


class AllocationCountTests(unittest.TestCase):

    def test_each_core_element_makes_one_instance_over_many_requests(self):
        counts = count_constructions(self, ElementDataDictionary)
        pipeline = PipelineBuilder().build()
        self.addCleanup(pipeline.close)
        for _ in range(REQUESTS):
            with process(pipeline):
                pass
        keys = {element.datakey for element in pipeline.flow_elements}
        self.assertEqual(
            {"sequence", "jsonbundler", "javascriptbuilder", "set-headers"},
            keys)
        self.assertEqual({key: 1 for key in keys}, counts)

    def test_requests_at_once_make_no_more_instances_than_the_bound(self):
        element = SequenceElement()
        element._element_data_pool.maximum_instances = BOUND
        counts = count_constructions(self, ElementDataDictionary)
        pipeline = build(element)
        for _ in range(REQUESTS // BOUND):
            open_flowdata = [process(pipeline) for _ in range(BOUND)]
            for flowdata in open_flowdata:
                flowdata.close()
        self.assertEqual({"sequence": BOUND}, counts)

    def test_the_pool_keeps_no_more_than_its_bound(self):
        element = SequenceElement()
        pool = element._element_data_pool
        pool.maximum_instances = BOUND
        pipeline = build(element)
        open_flowdata = [process(pipeline) for _ in range(BOUND * 2)]
        for flowdata in open_flowdata:
            flowdata.close()
        self.assertEqual(BOUND, len(pool))

    def test_threads_make_no_more_instances_than_run_at_once(self):
        counts = count_constructions(self, ElementDataDictionary)
        pipeline = build(PooledElement(THREADS))
        wrong = []

        def requests(name):
            for index in range(REQUESTS):
                with process(pipeline, name, index) as flowdata:
                    if flowdata.pooled.get(name) != index:
                        wrong.append((name, index))

        threads = [threading.Thread(target=requests, args=("t" + str(n),))
                   for n in range(THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([], wrong)
        self.assertLessEqual(counts["pooled"], THREADS)


class ReuseTests(unittest.TestCase):

    def test_a_reused_instance_has_no_values_from_the_last_request(self):
        pipeline = build(PooledElement())
        with process(pipeline, "first", 1) as flowdata:
            first = flowdata.get("pooled")
        with process(pipeline, "second", 2) as flowdata:
            second = flowdata.get("pooled")
            self.assertIs(first, second)
            self.assertIsNone(second.get("first"))
            self.assertEqual(2, second.get("second"))
            self.assertEqual("second", second.last_name)

    def test_a_reused_instance_is_written_and_then_finished_again(self):
        pipeline = build(PooledElement())
        process(pipeline, "first", 1).close()
        with process(pipeline, "second", 2) as flowdata:
            self.assertEqual({}, flowdata.errors)
            with self.assertRaises(Exception) as caught:
                flowdata.pooled.last_name = "after"
            self.assertIn(FINISHED, str(caught.exception))

    def test_a_core_element_reuses_its_instance_with_new_values(self):
        pipeline = build(SequenceElement())
        with process(pipeline) as flowdata:
            first = flowdata.sequence
            session = first.get("session-id")
        with process(pipeline) as flowdata:
            self.assertIs(first, flowdata.sequence)
            self.assertNotEqual(session, flowdata.sequence.get("session-id"))
            self.assertEqual(1, flowdata.sequence.get("sequence"))

    def test_closing_twice_gives_an_instance_back_once(self):
        element = PooledElement()
        pipeline = build(element)
        flowdata = process(pipeline)
        flowdata.close()
        flowdata.close()
        self.assertEqual(1, len(element._element_data_pool))
        with process(pipeline) as one, process(pipeline) as two:
            self.assertIsNot(one.pooled, two.pooled)

    def test_a_flow_data_not_closed_leaves_its_instances_to_the_gc(self):
        element = PooledElement()
        counts = count_constructions(self, ElementDataDictionary)
        pipeline = build(element)
        made = [weakref.ref(process(pipeline).pooled)
                for _ in range(REQUESTS)]
        gc.collect()
        self.assertEqual({"pooled": REQUESTS}, counts)
        self.assertEqual(0, len(element._element_data_pool))
        self.assertEqual([], [ref for ref in made if ref() is not None])


class PoolLookupTests(unittest.TestCase):

    def test_an_element_names_the_pool_it_keeps(self):
        element = SequenceElement()
        self.assertIs(element._element_data_pool,
                      element.get_element_data_pool())
        self.assertIsNone(FlowElement().get_element_data_pool())

    def test_an_attribute_that_is_not_a_pool_is_not_taken_for_one(self):
        element = OwnAttributeElement()
        pipeline = build(element)
        flowdata = process(pipeline)
        flowdata.close()
        self.assertIsNone(element.get_element_data_pool())
        self.assertEqual(1, flowdata.own.get("a"))


if __name__ == "__main__":
    unittest.main()

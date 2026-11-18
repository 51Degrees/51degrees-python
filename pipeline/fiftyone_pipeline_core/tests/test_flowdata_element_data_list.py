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
A Flow Data keeps its Element Data in a linked list, as the thread safety
page of the specification says. An add puts a new node at the head with a
plain write and takes no lock. A node never changes once added, so a reader
that has started sees a whole list, as it was when it read the head.
"""

import threading
import unittest

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class AddsItsData(FlowElement):
    """Adds Element Data holding its own name."""

    def __init__(self, datakey):
        super(AddsItsData, self).__init__()
        self.datakey = datakey

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter([])

    def process_internal(self, flowdata):
        flowdata.set_element_data(
            ElementDataDictionary(self, {"name": self.datakey}))


class ReadsWhileItAdds(AddsItsData):
    """Starts to list the Element Data already added, adds its own part way
    through, then finishes the list, as a reader on another thread would
    meet an add."""

    def process_internal(self, flowdata):
        values = flowdata.data.values()
        reading = iter(values)
        self.first = next(reading)
        super(ReadsWhileItAdds, self).process_internal(flowdata)
        self.rest = list(reading)
        self.taken_before = list(values)


def pipeline(*elements):
    builder = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False})
    for element in elements:
        builder.add(element)
    return builder.build()


def lock_types():
    return (type(threading.Lock()), type(threading.RLock()))


class ElementDataListTests(unittest.TestCase):

    def test_a_reader_part_way_through_is_not_upset_by_an_add(self):
        reader = ReadsWhileItAdds("reader")
        flowdata = pipeline(
            AddsItsData("one"), AddsItsData("two"), reader).create_flowdata()

        flowdata.process()

        names = [reader.first.name] + [data.name for data in reader.rest]
        self.assertEqual(["one", "two"], names)

    def test_a_view_taken_before_an_add_keeps_the_list_it_saw(self):
        reader = ReadsWhileItAdds("reader")
        flowdata = pipeline(
            AddsItsData("one"), AddsItsData("two"), reader).create_flowdata()

        flowdata.process()

        self.assertEqual(
            ["one", "two"], [data.name for data in reader.taken_before])
        self.assertEqual(
            ["one", "two", "reader"],
            [data.name for data in flowdata.data.values()])

    def test_element_data_is_listed_in_pipeline_order(self):
        flowdata = pipeline(
            AddsItsData("one"), AddsItsData("two"),
            AddsItsData("three")).create_flowdata()

        flowdata.process()

        self.assertEqual(["one", "two", "three"], list(flowdata.data))

    def test_the_newest_add_for_a_key_is_the_one_read(self):
        element = AddsItsData("one")
        flowdata = pipeline(element).create_flowdata()
        first = ElementDataDictionary(element, {"name": "first"})
        second = ElementDataDictionary(element, {"name": "second"})

        flowdata.set_element_data(first)
        flowdata.set_element_data(second)

        self.assertIs(second, flowdata.get("one"))
        self.assertEqual(["one"], list(flowdata.data))

    def test_an_add_takes_no_lock(self):
        """A smoke test. It looks only at the FlowData's own attributes, so
        a lock kept anywhere else would not be seen."""
        flowdata = pipeline(AddsItsData("one")).create_flowdata()

        flowdata.process()

        held = [name for name, value in vars(flowdata).items()
                if isinstance(value, lock_types())]
        self.assertEqual([], held)

    def test_a_write_through_a_view_shows_in_that_view(self):
        element = AddsItsData("one")
        flowdata = pipeline(element).create_flowdata()
        view = flowdata.data
        first = ElementDataDictionary(element, {"name": "first"})
        second = ElementDataDictionary(element, {"name": "second"})
        third = ElementDataDictionary(element, {"name": "third"})

        view["first"] = first
        view.update({"second": second})
        view.setdefault("third", third)

        self.assertIs(first, view["first"])
        self.assertIs(second, view["second"])
        self.assertIs(third, view["third"])
        self.assertEqual(["first", "second", "third"], list(view))
        self.assertIs(first, flowdata.get("first"))

    def test_a_copy_is_a_dict_of_the_element_data(self):
        flowdata = pipeline(
            AddsItsData("one"), AddsItsData("two")).create_flowdata()
        flowdata.process()

        copy = flowdata.data.copy()

        self.assertIs(dict, type(copy))
        self.assertEqual(["one", "two"], list(copy))
        self.assertIs(flowdata.get("two"), copy["two"])

    def test_element_data_is_not_removed(self):
        flowdata = pipeline(
            AddsItsData("one"), AddsItsData("two")).create_flowdata()
        flowdata.process()

        def remove(view):
            del view["one"]

        for removal in (
                remove,
                lambda view: view.pop("one"),
                lambda view: view.popitem(),
                lambda view: view.clear()):
            with self.assertRaises(TypeError):
                removal(flowdata.data)
        self.assertEqual(["one", "two"], list(flowdata.data))

    def test_setting_data_copies_the_mapping_given(self):
        element = AddsItsData("one")
        flowdata = pipeline(element).create_flowdata()
        given = {"one": ElementDataDictionary(element, {"name": "one"})}

        flowdata.data = given
        given["two"] = ElementDataDictionary(element, {"name": "two"})

        self.assertEqual(["one"], list(flowdata.data))

    def test_setting_data_replaces_the_whole_list_at_once(self):
        element = AddsItsData("one")
        flowdata = pipeline(element).create_flowdata()
        flowdata.data = {
            "old": ElementDataDictionary(element, {"name": "old"})}
        seen = []

        class Contents(dict):
            # Lists the Element Data part way through the replacement, as
            # a reader on another thread could.
            def items(self):
                for key, value in dict.items(self):
                    yield key, value
                    seen.append(list(flowdata.data))

        flowdata.data = Contents({
            "a": ElementDataDictionary(element, {"name": "a"}),
            "b": ElementDataDictionary(element, {"name": "b"})})

        self.assertEqual([["old"], ["old"]], seen)
        self.assertEqual(["a", "b"], list(flowdata.data))

    def test_a_reader_on_another_thread_always_sees_a_whole_list(self):
        element = AddsItsData("one")
        flowdata = pipeline(element).create_flowdata()
        keys = ["key%d" % index for index in range(2000)]
        seen = []
        failures = []
        done = threading.Event()

        def read():
            try:
                while not done.is_set():
                    listed = list(flowdata.data)
                    # A whole list is every key added so far, in order.
                    if listed != keys[:len(listed)]:
                        failures.append(listed)
                    seen.append(len(listed))
            except Exception as error:
                failures.append(error)

        reader = threading.Thread(target=read)
        reader.start()
        try:
            for key in keys:
                flowdata.data[key] = ElementDataDictionary(
                    element, {"name": key})
        finally:
            done.set()
            reader.join()

        self.assertEqual([], failures)
        self.assertTrue(seen)
        self.assertEqual(keys, list(flowdata.data))


if __name__ == "__main__":
    unittest.main()

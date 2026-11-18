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
        flowdata = pipeline(AddsItsData("one")).create_flowdata()

        flowdata.process()

        held = [name for name, value in vars(flowdata).items()
                if isinstance(value, lock_types())]
        self.assertEqual([], held)


if __name__ == "__main__":
    unittest.main()

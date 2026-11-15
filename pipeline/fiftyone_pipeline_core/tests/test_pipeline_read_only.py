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

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# The errors Python raises for a change to a collection that cannot be
# changed.
READ_ONLY = (AttributeError, TypeError)


class CountingElement(FlowElement):

    """!
    An element that counts the times it processes, and accepts the header
    named after its data key.

    """

    def __init__(self, datakey):
        super(CountingElement, self).__init__()
        self.datakey = datakey
        self.calls = 0

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["header." + self.datakey])

    def process_internal(self, flowdata):
        self.calls += 1


class RegistrationElement(CountingElement):

    """!
    An element that records what the pipeline holds when the element is
    registered with it.

    """

    def on_registration(self, pipeline):
        self.keys_seen = list(pipeline.flow_elements_list)
        self.elements_seen = len(pipeline.flow_elements)


def builder(*elements):
    # Only the elements given, so the pipeline's order and length are known.
    result = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False})
    for element in elements:
        result.add(element)
    return result


def build(*elements):
    return builder(*elements).build()


def process(pipeline):
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    return flowdata


def accepts(pipeline, key):
    return pipeline.get_evidence_key_filter().filter_evidence_key(key)


class PipelineCannotBeChangedTests(unittest.TestCase):

    # Appending an element to a built pipeline raises, and the element does
    # not run.
    def test_appending_an_element_raises_and_it_does_not_run(self):
        first = CountingElement("first")
        pipeline = build(first)
        added = CountingElement("added")

        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements.append(added)

        process(pipeline)
        self.assertEqual([1, 0], [first.calls, added.calls])
        self.assertEqual(1, len(pipeline.flow_elements))

    # Replacing or removing an element raises, and every element the
    # pipeline was built with still runs.
    def test_replacing_or_removing_an_element_raises(self):
        first = CountingElement("first")
        second = CountingElement("second")
        pipeline = build(first, second)
        other = CountingElement("other")

        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements[0] = other
        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements.remove(second)
        with self.assertRaises(READ_ONLY):
            del pipeline.flow_elements[0]

        process(pipeline)
        self.assertEqual(
            [1, 1, 0], [first.calls, second.calls, other.calls])

    # Adding to the elements by data key raises, and the pipeline neither
    # finds the element nor accepts its evidence.
    def test_adding_to_the_lookup_raises_and_changes_nothing(self):
        first = CountingElement("first")
        pipeline = build(first)
        added = CountingElement("added")

        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements_list["added"] = added
        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements_list.update({"added": added})

        self.assertEqual(["first"], list(pipeline.flow_elements_list))
        with self.assertRaises(KeyError):
            pipeline.get_element("added")
        self.assertFalse(accepts(pipeline, "header.added"))
        process(pipeline)
        self.assertEqual([1, 0], [first.calls, added.calls])

    # Removing from the elements by data key raises, and the pipeline still
    # finds the element and accepts its evidence.
    def test_removing_from_the_lookup_raises_and_changes_nothing(self):
        first = CountingElement("first")
        pipeline = build(first)

        with self.assertRaises(READ_ONLY):
            del pipeline.flow_elements_list["first"]
        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements_list.pop("first")

        self.assertIs(first, pipeline.get_element("first"))
        self.assertTrue(accepts(pipeline, "header.first"))

    # The data keys an error message lists cannot be changed either.
    def test_changing_the_data_keys_in_messages_raises(self):
        pipeline = build(CountingElement("first"))

        with self.assertRaises(READ_ONLY):
            pipeline.flow_elements_display_list.append("added")

        self.assertEqual(
            ["first"], list(pipeline.flow_elements_display_list))

    # The pipeline keeps its own copy of the elements it is given, so
    # changing the caller's list afterwards changes nothing.
    def test_changing_the_list_given_to_the_pipeline_changes_nothing(self):
        first = CountingElement("first")
        elements = [first]
        pipeline = Pipeline(elements)
        added = CountingElement("added")

        elements.append(added)

        process(pipeline)
        self.assertEqual([1, 0], [first.calls, added.calls])
        self.assertEqual(1, len(pipeline.flow_elements))


class PipelineReadTests(unittest.TestCase):

    # The elements read in order, by index, by length and by membership.
    def test_reading_the_elements(self):
        first = CountingElement("first")
        second = CountingElement("second")
        pipeline = build(first, second)

        self.assertEqual(2, len(pipeline.flow_elements))
        self.assertIs(first, pipeline.flow_elements[0])
        self.assertIs(second, pipeline.flow_elements[-1])
        self.assertEqual([first, second], list(pipeline.flow_elements))
        self.assertEqual(
            ["first", "second"],
            [element.datakey for element in pipeline.flow_elements])
        self.assertIn(second, pipeline.flow_elements)
        self.assertEqual(1, pipeline.flow_elements.index(second))

    # The elements by data key read by key, in the order they were added,
    # and through get_element.
    def test_reading_the_lookup(self):
        first = CountingElement("first")
        second = CountingElement("second")
        pipeline = build(first, second)

        self.assertIs(first, pipeline.get_element("first"))
        self.assertIs(second, pipeline.flow_elements_list["second"])
        self.assertIn("first", pipeline.flow_elements_list)
        self.assertEqual(2, len(pipeline.flow_elements_list))
        self.assertEqual(
            ["first", "second"], list(pipeline.flow_elements_list))
        self.assertEqual(
            [first, second], list(pipeline.flow_elements_list.values()))
        self.assertIsNone(pipeline.flow_elements_list.get("missing"))
        with self.assertRaises(KeyError):
            pipeline.get_element("missing")
        self.assertEqual(
            ["first", "second"], list(pipeline.flow_elements_display_list))
        self.assertTrue(accepts(pipeline, "header.second"))

    # Processing runs each element once.
    def test_processing_runs_every_element(self):
        first = CountingElement("first")
        second = CountingElement("second")

        process(build(first, second))

        self.assertEqual([1, 1], [first.calls, second.calls])

    # An element being registered finds every element in the pipeline, and
    # by data key those registered before it, which is how an element finds
    # one it depends on.
    def test_an_element_sees_those_before_it_when_registered(self):
        first = RegistrationElement("first")
        second = RegistrationElement("second")

        build(first, second)

        self.assertEqual([], first.keys_seen)
        self.assertEqual(["first"], second.keys_seen)
        self.assertEqual([2, 2], [first.elements_seen, second.elements_seen])

    # Adding to the builder after build leaves the built pipeline as it was.
    def test_adding_to_the_builder_after_build_changes_nothing(self):
        first = CountingElement("first")
        pipeline_builder = builder(first)
        pipeline = pipeline_builder.build()
        added = CountingElement("added")

        pipeline_builder.add(added)

        process(pipeline)
        self.assertEqual([1, 0], [first.calls, added.calls])
        self.assertEqual(1, len(pipeline.flow_elements))

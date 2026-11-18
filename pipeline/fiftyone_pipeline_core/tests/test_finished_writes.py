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
A FlowData that has finished processing refuses Evidence, ElementData and
errors, and ElementData refuses a write once the FlowElement that writes it
has finished, as the thread safety page of the specification requires. The
last tests process every FlowElement this package defines, and its example
FlowElements, then write to each one's ElementData and expect the error.
"""

import copy
import importlib
import importlib.util
import inspect
import json
import os
import pkgutil
import unittest

import fiftyone_pipeline_core
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.flowerror import FlowError
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

FINISHED = "finished processing"

# FlowElements that only other FlowElements build on, which have no
# ElementData of their own to write.
BASES = {FlowElement}

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class WritingElement(FlowElement):
    """Adds data and then writes it, as a FlowElement may while it
    processes."""

    def __init__(self, datakey="writer", value="first"):
        super(WritingElement, self).__init__()
        self.datakey = datakey
        self.value = value

    def process_internal(self, flowdata):
        data = flowdata.data.get(self.datakey)
        if data is None:
            data = ElementDataDictionary(self, {})
            flowdata.set_element_data(data)
        data.written = self.value


class AddingElement(FlowElement):
    """Adds data under another FlowElement's key, and a value to its
    contents while it processes."""

    def __init__(self):
        super(AddingElement, self).__init__()
        self.datakey = "adder"

    def process_internal(self, flowdata):
        data = ElementDataDictionary(WritingElement("other"), {})
        data.contents["item"] = "while processing"
        flowdata.set_element_data(data)


def item_store(data):
    """The dictionary the data keeps its values in, or None."""
    if isinstance(data, dict):
        return data
    if (isinstance(getattr(type(data), "contents", None), property)
            or "contents" in vars(data)):
        return data.contents
    return None


# Each way a dictionary can be written.
DICT_WRITES = (
    ("[]=", lambda d: d.__setitem__("b", 2)),
    ("del", lambda d: d.__delitem__("a")),
    ("update", lambda d: d.update(b=2)),
    ("pop", lambda d: d.pop("a")),
    ("popitem", lambda d: d.popitem()),
    ("setdefault", lambda d: d.setdefault("b", 2)),
    ("clear", lambda d: d.clear()),
    ("|=", lambda d: d.__ior__({"b": 2})),
)


def process(*elements, **settings):
    builder = PipelineBuilder(dict({"add_javascript_builder": False,
                                    "use_setheader_properties": False},
                                   **settings))
    for element in elements:
        builder.add(element)
    flowdata = builder.build().create_flowdata()
    flowdata.process()
    return flowdata


def load_example(name):
    """An example module, loaded from its file under its own name."""
    spec = importlib.util.spec_from_file_location(
        "example_" + name, os.path.join(EXAMPLES, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def defined_flow_elements(package):
    """Every FlowElement class defined in the package's own modules."""
    found = set()
    for module in pkgutil.walk_packages(package.__path__,
                                        package.__name__ + "."):
        loaded = importlib.import_module(module.name)
        for _, cls in inspect.getmembers(loaded, inspect.isclass):
            if (issubclass(cls, FlowElement)
                    and cls.__module__.startswith(package.__name__)):
                found.add(cls)
    return found


class FinishedFlowDataTests(unittest.TestCase):

    def test_evidence_cannot_be_added_once_processed(self):
        flowdata = process(WritingElement())
        with self.assertRaises(Exception) as caught:
            flowdata.evidence.add("query.later", "value")
        self.assertIn(FINISHED, str(caught.exception))
        with self.assertRaises(Exception) as caught:
            flowdata.evidence.add_from_dict({"query.later": "value"})
        self.assertIn(FINISHED, str(caught.exception))
        self.assertIsNone(flowdata.evidence.get("query.later"))

    def test_element_data_cannot_be_added_once_processed(self):
        element = WritingElement("late")
        flowdata = process(WritingElement())
        with self.assertRaises(Exception) as caught:
            flowdata.set_element_data(ElementDataDictionary(element, {}))
        self.assertIn(FINISHED, str(caught.exception))
        self.assertNotIn("late", flowdata.data)

    def test_errors_cannot_be_added_once_processed(self):
        flowdata = process(WritingElement())
        with self.assertRaises(Exception) as caught:
            flowdata.set_error(FlowError("late", Exception("late"), ""))
        self.assertIn(FINISHED, str(caught.exception))
        self.assertEqual({}, flowdata.errors)

    def test_a_second_process_raises_even_when_exceptions_are_suppressed(self):
        flowdata = process(WritingElement(),
                           suppress_process_exceptions=True)
        with self.assertRaises(Exception) as caught:
            flowdata.process()
        self.assertIn("already processed", str(caught.exception))
        self.assertEqual({}, flowdata.errors)

    def test_evidence_can_be_added_before_processing(self):
        flowdata = PipelineBuilder().add(WritingElement()).build() \
            .create_flowdata()
        flowdata.evidence.add("query.early", "value")
        self.assertEqual("value", flowdata.evidence.get("query.early"))


class FinishedElementDataTests(unittest.TestCase):

    def test_data_written_while_processing_cannot_be_written_after(self):
        flowdata = process(WritingElement())
        data = flowdata.get("writer")
        self.assertEqual("first", data.written)
        with self.assertRaises(Exception) as caught:
            data.written = "after"
        self.assertIn(FINISHED, str(caught.exception))
        self.assertEqual("first", data.written)

    def test_an_element_sharing_the_data_writes_it_while_it_processes(self):
        flowdata = process(WritingElement("shared", "first"),
                           WritingElement("shared", "second"))
        data = flowdata.get("shared")
        self.assertEqual("second", data.written)
        with self.assertRaises(Exception):
            data.written = "after"

    def test_the_data_keeps_its_own_state_once_finished(self):
        data = process(WritingElement()).get("writer")
        data._kept = "a value kept once read"
        self.assertEqual("a value kept once read", data._kept)

    def test_the_contents_cannot_be_written_once_finished(self):
        for name, write in DICT_WRITES:
            with self.subTest(name):
                data = process(WritingElement()).get("writer")
                dict.__setitem__(data.contents, "a", 1)
                for contents in (data.contents, data.as_dictionary()):
                    with self.assertRaises(Exception) as caught:
                        write(contents)
                    self.assertIn(FINISHED, str(caught.exception))
                self.assertEqual({"a": 1}, dict(data.contents))

    def test_the_contents_cannot_be_replaced_once_finished(self):
        data = process(WritingElement()).get("writer")
        with self.assertRaises(Exception) as caught:
            data.contents = {"b": 2}
        self.assertIn(FINISHED, str(caught.exception))
        self.assertEqual({}, dict(data.contents))

    def test_the_contents_are_a_dict_that_is_written_while_processing(self):
        flowdata = process(AddingElement())
        contents = flowdata.get("other").contents
        self.assertIsInstance(contents, dict)
        self.assertEqual({"item": "while processing"}, contents)
        self.assertEqual('{"item": "while processing"}',
                         json.dumps(contents))
        self.assertIs(dict, type(copy.deepcopy(contents)))
        self.assertIs(dict, type(contents.copy()))

    def test_closing_the_flow_data_is_not_a_write(self):
        class ClosingData(ElementDataDictionary):
            def close(self):
                self.closed = True

        class ClosingElement(FlowElement):
            def __init__(self):
                super(ClosingElement, self).__init__()
                self.datakey = "closing"

            def process_internal(self, flowdata):
                flowdata.set_element_data(ClosingData(self, {}))

        flowdata = process(ClosingElement())
        flowdata.close()
        self.assertTrue(flowdata.get("closing").closed)


class EveryFlowElementTests(unittest.TestCase):

    def assert_writes_fail(self, flowdata, key):
        data = flowdata.get(key)
        with self.assertRaises(Exception) as caught:
            data.written_after_processing = True
        self.assertIn(FINISHED, str(caught.exception))
        contents = item_store(data)
        if contents is not None:
            with self.assertRaises(Exception) as caught:
                contents["written_after_processing"] = True
            self.assertIn(FINISHED, str(caught.exception))

    def test_the_package_flow_elements_refuse_writes_once_finished(self):
        flowdata = PipelineBuilder().build().create_flowdata()
        flowdata.evidence.add("header.user-agent", "a user agent")
        flowdata.process()
        processed = set()
        for element in flowdata.pipeline.flow_elements:
            self.assert_writes_fail(flowdata, element.datakey)
            processed.add(type(element))
        self.assertEqual(
            defined_flow_elements(fiftyone_pipeline_core) - BASES, processed)

    def test_the_example_flow_elements_refuse_writes_once_finished(self):
        for name, element in (
                ("simple_flow_element", "SimpleFlowElement"),
                ("client_side_evidence_custom_flow_element",
                 "AstrologyFlowElement")):
            module = load_example(name)
            builder = PipelineBuilder({"add_javascript_builder": False,
                                       "use_setheader_properties": False})
            flowdata = builder.add(getattr(module, element)()).build() \
                .create_flowdata()
            flowdata.evidence.add("query.dateOfBirth", "1992-12-18")
            flowdata.process()
            self.assert_writes_fail(flowdata, "astrology")


if __name__ == "__main__":
    unittest.main()

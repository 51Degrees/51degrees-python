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
Every FlowElement this package defines is processed, then a write to its
ElementData is expected to fail, as the thread safety page of the
specification requires.
"""

import importlib
import inspect
import json
import pkgutil
import unittest

import fiftyone_location
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_location.location_cloud import LocationCloud

FINISHED = "finished processing"


def item_store(data):
    """The dictionary the data keeps its values in."""
    if isinstance(data, dict):
        return data
    return data.contents


# FlowElements that only other FlowElements build on.
BASES = set()


class StandInRequestEngine(FlowElement):
    """Stands in for a Cloud Request Engine whose answer has an empty
    section for each of the given data keys."""

    def __init__(self, keys):
        super(StandInRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.flow_element_properties = {key: {} for key in keys}
        self.answer = json.dumps({key: {} for key in keys})

    def process_internal(self, flowdata):
        flowdata.set_element_data(
            ElementDataDictionary(self, {"cloud": self.answer}))


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


class FinishedWritesTests(unittest.TestCase):

    def test_every_flow_element_refuses_writes_once_finished(self):
        processed = set()
        for element in [LocationCloud()]:
            builder = PipelineBuilder({"add_javascript_builder": False,
                                       "use_setheader_properties": False})
            flowdata = builder \
                .add(StandInRequestEngine([element.datakey])) \
                .add(element).build().create_flowdata()
            flowdata.process()
            data = flowdata.get(element.datakey)
            with self.assertRaises(Exception) as caught:
                data.written_after_processing = True
            self.assertIn(FINISHED, str(caught.exception))
            with self.assertRaises(Exception) as caught:
                item_store(data)["written_after_processing"] = True
            self.assertIn(FINISHED, str(caught.exception))
            processed.add(type(element))
        self.assertEqual(
            defined_flow_elements(fiftyone_location) - BASES, processed)


if __name__ == "__main__":
    unittest.main()
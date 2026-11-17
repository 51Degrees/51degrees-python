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
import pkgutil
import unittest

import fiftyone_pipeline_translation
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_translation.translation_engine_base import (
    TranslationEngineBase)

FINISHED = "finished processing"


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


class SourceElement(FlowElement):
    """Gives fixed names to translate."""

    def __init__(self):
        super(SourceElement, self).__init__()
        self.datakey = "source"

    def process_internal(self, flowdata):
        flowdata.set_element_data(
            ElementDataDictionary(self, {"names": ["Germany"]}))


class FinishedWritesTests(unittest.TestCase):

    def test_every_flow_element_refuses_writes_once_finished(self):
        engine = TranslationEngineBase(
            "source", [("Names", "NamesTranslated")],
            {"countries.fr_FR.yml": "Germany: Allemagne\n"}, "fr_FR")
        flowdata = PipelineBuilder().add(SourceElement()).add(engine) \
            .build().create_flowdata()
        flowdata.process()
        data = flowdata.get(engine.datakey)
        with self.assertRaises(Exception) as caught:
            data.written_after_processing = True
        self.assertIn(FINISHED, str(caught.exception))
        self.assertEqual(
            {TranslationEngineBase},
            defined_flow_elements(fiftyone_pipeline_translation))


if __name__ == "__main__":
    unittest.main()
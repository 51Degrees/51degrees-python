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
The engines package defines only the Engine that other FlowElements build
on. Its example engine is processed, then a write to its ElementData is
expected to fail, as the thread safety page of the specification requires.
"""

import importlib
import importlib.util
import inspect
import os
import pkgutil
import unittest

import fiftyone_pipeline_engines
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.engine import Engine

FINISHED = "finished processing"


def item_store(data):
    """The dictionary the data keeps its values in."""
    if isinstance(data, dict):
        return data
    return data.contents


EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


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

    def test_the_package_defines_only_the_engine_others_build_on(self):
        self.assertEqual(
            {Engine}, defined_flow_elements(fiftyone_pipeline_engines))

    def test_the_example_engine_refuses_writes_once_finished(self):
        spec = importlib.util.spec_from_file_location(
            "example_simple_onpremise_engine",
            os.path.join(EXAMPLES, "simple_onpremise_engine.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        engine = module.SimpleOnPremiseEngine(module.DATA_FILE)
        pipeline = PipelineBuilder({"add_javascript_builder": False,
                                    "use_setheader_properties": False}) \
            .add(engine).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add(module.DATE_OF_BIRTH, "1992-12-18")
        flowdata.process()
        with self.assertRaises(Exception) as caught:
            flowdata.get("astrology").written_after_processing = True
        self.assertIn(FINISHED, str(caught.exception))
        with self.assertRaises(Exception) as caught:
            item_store(flowdata.get("astrology"))["written_after_processing"] = True
        self.assertIn(FINISHED, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
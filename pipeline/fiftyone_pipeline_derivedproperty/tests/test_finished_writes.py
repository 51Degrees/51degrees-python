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
Every FlowElement this package defines, and the one its example defines, is
processed, then a write to its ElementData is expected to fail, as the
thread safety page of the specification requires. The derived property
elements of a pipeline share one ElementData, which each writes while it
processes and none writes once they have all finished.
"""

import importlib
import importlib.util
import inspect
import os
import pkgutil

import pytest

import fiftyone_pipeline_derivedproperty
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_derivedproperty import DerivedPropertyElementBuilder
from fiftyone_pipeline_derivedproperty.derived_property_element import \
    DerivedPropertyElement

from .helpers import SourceElement, band_script, pipeline_of, processed

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


def derived(name):
    return (DerivedPropertyElementBuilder()
            .add_script(name, band_script(name, "src.N")).build())


def test_every_derived_element_writes_only_while_it_processes():
    flowdata = processed(pipeline_of(
        [SourceElement("src", {"N": 12}), derived("Demo"), derived("Other")]))
    data = flowdata.derived
    assert data.get("Demo").value() == "High"
    assert data.get("Other").value() == "High"
    with pytest.raises(Exception, match=FINISHED):
        data.set_value("Demo", "written after processing")
    with pytest.raises(Exception, match=FINISHED):
        data.written_after_processing = True
    with pytest.raises(Exception, match=FINISHED):
        item_store(data)["written_after_processing"] = True
    assert data.get("Demo").value() == "High"
    assert defined_flow_elements(fiftyone_pipeline_derivedproperty) == \
        {DerivedPropertyElement}


def test_the_example_flow_element_refuses_writes_once_finished():
    spec = importlib.util.spec_from_file_location(
        "example_screen_element", os.path.join(EXAMPLES, "screen_element.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    flowdata = processed(pipeline_of([module.ScreenElement()]))
    with pytest.raises(Exception, match=FINISHED):
        flowdata.get("screen").written_after_processing = True
    with pytest.raises(Exception, match=FINISHED):
        item_store(flowdata.get("screen"))["written_after_processing"] = True

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

import os

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

## The derived-properties submodule in this checkout.
SUBMODULE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src",
    "fiftyone_pipeline_derivedproperty", "derived-properties")


def as_element_gives(value, wrap):
    """!
    A value as a case file writes it, as a 51Degrees element gives it. A
    value with a no value message is an AspectPropertyValue without a
    value, and a weighted list has the value and weighting fields the
    IP Intelligence engines give.
    """
    if isinstance(value, dict):
        if "NoValue" in value:
            return AspectPropertyValue(value["NoValue"])
        if "String" in value:
            return (AspectPropertyValue(None, value["String"]) if wrap
                    else value["String"])
    if isinstance(value, list) and wrap:
        return AspectPropertyValue(None, [
            {"value": m["Value"], "weighting": m.get("Weight")}
            if isinstance(m, dict) and "Value" in m else m
            for m in value])
    return AspectPropertyValue(None, value) if wrap else value


class SourceElement(FlowElement):
    """!
    An element giving fixed values under one element data key, as plain
    element data. It lists the properties it supplies, which need not be
    the ones it has a value for.
    """

    def __init__(self, datakey, values, supplies=None, wrap=True):
        super().__init__()
        self.datakey = datakey
        self.values = values
        self.wrap = wrap
        names = list(values.keys()) if supplies is None else supplies
        self.properties = {
            name.lower(): {"name": name, "type": "string"} for name in names}

    def process_internal(self, flowdata):
        contents = {name: as_element_gives(value, self.wrap)
                    for name, value in self.values.items()}
        flowdata.set_element_data(ElementDataDictionary(self, contents))


class RecordingLogger(Logger):
    """! A logger keeping every line, debug included. """

    def __init__(self):
        super().__init__(min_level="debug")
        self.lines = []

    def log_internal(self, level, log):
        self.lines.append((level, log["message"]))

    def messages(self, level):
        return [message for logged, message in self.lines if logged == level]


def band_script(name, prop, version="1.0.0", extra=""):
    """! The text of a small script reading one source property. """
    lines = [
        "Format: 1",
        "Name: " + name,
        "Version: " + version,
        extra,
        "Output:",
        "  Name: " + name,
        "  Description: Whether a number is ten or more.",
        "  ValueType: string",
        "  IsList: false",
        "  Category: Testing",
        "Rules:",
        "  - When: { Property: " + prop + ", Ge: 10 }",
        "    Then: High",
        "  - Else: Low"
    ]
    return "\n".join(line for line in lines if line != "")


def pipeline_of(elements, logger=None, **settings):
    """! Builds a pipeline holding the elements given, with nothing added. """
    builder = PipelineBuilder(dict({
        "add_javascript_builder": False,
        "use_setheader_properties": False
    }, **settings))
    if logger is not None:
        builder.add_logger(logger)
    for element in elements:
        builder.add(element)
    return builder.build()


def processed(pipeline):
    """! Processes a request through a pipeline. """
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    return flowdata


def submodule_text(*parts):
    """! Reads a file in the submodule. """
    with open(os.path.join(SUBMODULE, *parts), encoding="utf-8") as file:
        return file.read()

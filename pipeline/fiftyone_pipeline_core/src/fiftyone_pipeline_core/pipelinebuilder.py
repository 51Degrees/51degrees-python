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

from .pipeline import Pipeline
from .logger import Logger
from .javascriptbuilder import JavascriptBuilderElement
from .jsonbundler import JSONBundlerElement
from .sequenceelement import SequenceElement
from .setheaderelement import SetHeaderElement
import importlib

# The data keys of the JSONBundler and the JavaScriptBuilder.
JSON_BUILDER_KEY = "jsonbundler"
JAVASCRIPT_BUILDER_KEY = "javascriptbuilder"


def _data_key(element):

    # Flow data keeps each element's results under its data key in lower
    # case, so two keys that differ only in letters are the same key.
    return str(element.datakey).lower()


class PipelineBuilder(object):
    """
    A PipelineBuilder generates a Pipeline object
    Before construction of the Pipeline, FlowElements are added to it
    There are also options for how JavaScript is output from the Pipeline

    """

    def __init__(self, settings= {}):
        """
        Pipeline Builder constructor.
        The SequenceElement, JSONBundler, JavaScriptBuilder and
        SetHeaderElement switches below each add their element only when the
        caller has not added one with the same data key.
        @type settings: dictionary
        @param settings : settings for the pipeline builder including:
        `add_javascript_builder (Bool)` - Whether to add the JavaScriptBuilder, with the
        JSONBundler and SequenceElement it works with, to the pipeline (default true).
        Set to False to add none of the three.
        `add_sequence_element (Bool)` - Whether to add the SequenceElement, as the first
        element of the pipeline (default true)
        `add_json_builder_element (Bool)` - Whether to add the JSONBundler (default true).
        The JavaScriptBuilder reads its output, so a pipeline that keeps the
        JavaScriptBuilder needs a JSONBundler, added here or by the caller.
        `add_javascript_builder_element (Bool)` - Whether to add the JavaScriptBuilder
        alone (default true)
        `javascript_builder_settings (dict)` - Settings for the JavaScriptBuilder engine 
        @rtype: PipelineBuilder
        `use_setheader_properties (Bool)` - Whether to add the SetHeaderElement to the pipeline
        (default true)
        `add_set_header_element (Bool)` - Whether to add the SetHeaderElement alone
        (default true). It is added only when this and use_setheader_properties
        are both true.
        `suppress_process_exceptions (Bool)` - If False (the default) the first error thrown
        while processing is re-raised from flow_data.process(); if True, errors are stored on
        flow_data.errors and process() returns normally. Recommended True for web apps so a
        processing failure degrades gracefully instead of failing the request.
        `auto_close_elements (Bool)` - Whether closing the pipeline closes its flow elements
        (default true). Set to False when the elements are shared with another pipeline,
        and close each element once every pipeline using it is finished with.
        @return: Returns a Pipeline Builder

        """

        self.flow_elements = []
        self.logger = Logger()

        if "add_javascript_builder" in settings:
            self.add_javaScriptbuilder = settings["add_javascript_builder"]
        else:
            self.add_javaScriptbuilder = True
          
        self.add_sequence_element = settings.get("add_sequence_element", True)
        self.add_json_builder_element = settings.get(
            "add_json_builder_element", True)
        self.add_javascript_builder_element = settings.get(
            "add_javascript_builder_element", True)
        self.add_set_header_element = settings.get(
            "add_set_header_element", True)

        if "javascript_builder_settings" in settings:
            self.javascriptbuilder_settings = settings["javascript_builder_settings"]

        if "use_setheader_properties" in settings:
            self.use_setheader_properties = settings["use_setheader_properties"]
        else:
            self.use_setheader_properties = True

        if "data_file_update_service" in settings:
            self.data_file_update_service = settings["data_file_update_service"]
        else:
            self.data_file_update_service = None

        if "suppress_process_exceptions" in settings:
            self.suppress_process_exceptions = settings["suppress_process_exceptions"]
        else:
            self.suppress_process_exceptions = False

        if "auto_close_elements" in settings:
            self.auto_close_elements = settings["auto_close_elements"]
        else:
            self.auto_close_elements = True

    def get_sequence_elements(self):
        """
        The SequenceElement, to be the first element of the pipeline, unless
        add_javascript_builder or add_sequence_element is false
        @rtype: list
        @return: Returns a list of FlowElements
        """

        if self.add_javaScriptbuilder and self.add_sequence_element:
            return [SequenceElement()]

        return []

    def get_javascript_elements(self):
        """
        The JSONBundler and the JavaScriptBuilder, to be added after the other
        elements. Neither is added if add_javascript_builder is false, and
        each has its own switch (add_json_builder_element and
        add_javascript_builder_element).
        @rtype: list
        @return: Returns a list of FlowElements     
        """
        
        flow_elements = []

        if (self.add_javaScriptbuilder):

            if self.add_json_builder_element:
                flow_elements.append(JSONBundlerElement())

            if self.add_javascript_builder_element:
                if (hasattr(self, "javascriptbuilder_settings")):
                    flow_elements.append(JavascriptBuilderElement(self.javascriptbuilder_settings))
                else:
                    flow_elements.append(JavascriptBuilderElement())
   
        return flow_elements

    def get_setheader_elements(self):
        """
        Adds the SetHeaderElement to the pipeline if
        If use_setheader_properties and add_set_header_element are true (the default)
        @rtype: list
        @return: Returns a list of FlowElements     
        """
        
        flow_elements = []

        if self.use_setheader_properties and self.add_set_header_element:
            flow_elements.append(SetHeaderElement())
   
        return flow_elements

    def add(self, flow_element):
        """
        Add a flow_element to a list of flowElements be used in a pipeline.
        
        @type flow_element: FlowElement
        @param flow_element: flowElement to be added to the pipeline

        @rtype: PipelineBuilder
        @return: Returns the pipleine builder with the specified flowElement added to it's list of flowElements.

        """

        self.flow_elements.append(flow_element)

        return self

    def build(self):
        """
        Construct an immutable Pipeline using the list of flowElements, (Engines) and (Logger) currently in this Pipeline Builder.
        Call build after all items to be included in the pipeline have been added.

        @rtype: Pipeline
        @return: Returns a Pipeline

        """

        flow_elements = self._add_web_elements(self.flow_elements)

        return Pipeline(flow_elements, logger=self.logger, suppress_process_exceptions=self.suppress_process_exceptions, data_file_update_service=self.data_file_update_service, auto_close_elements=self.auto_close_elements)

    def _add_web_elements(self, flow_elements):

        """!
        The caller's elements with each web integration element the settings
        ask for, unless the caller added one with the same data key. The
        SequenceElement goes first and the others after every other element,
        except that a JSONBundler goes immediately before a JavaScriptBuilder
        the caller added, because the JavaScriptBuilder reads the
        JSONBundler's results.

        @type flow_elements: list
        @param flow_elements: The FlowElements the caller added
        @rtype: list
        @return: Returns a new list of FlowElements
        """

        present = set(_data_key(element) for element in flow_elements)

        def absent(element):
            return _data_key(element) not in present

        elements = [element for element in self.get_sequence_elements()
                    if absent(element)]
        elements.extend(flow_elements)

        for element in self.get_javascript_elements():
            if not absent(element):
                continue
            builder = next(
                (index for index, added in enumerate(elements)
                 if _data_key(added) == JAVASCRIPT_BUILDER_KEY),
                None)
            if _data_key(element) == JSON_BUILDER_KEY and builder is not None:
                elements.insert(builder, element)
            else:
                elements.append(element)

        elements.extend(element for element in self.get_setheader_elements()
                        if absent(element))

        return elements

    def add_logger(self, logger):
        """
        Add an instance of the logger class to the pipeline.

        @type logger: Logger
        @param logger: Logger to be added to the pipeline

        @rtype: PipelineBuilder
        @return: Returns the pipeline builder with the specified Logger added.
        
        """

        self.logger = logger

        return self

    def build_from_configuration(self, config):
        """
        Build a pipeline from a configuration file

        @type config: dict
        @param config: pipeline configuration

        @rtype: Pipeline
        @return: Returns built pipeline
        
        If an element fails to build, the elements already built are closed
        and the error is raised.

        """

        flow_elements = []

        try:
            for element in config["PipelineOptions"]["Elements"]:
                flow_element = importlib.import_module(element["elementPath"]).__getattribute__(element["elementName"])
                if("elementParameters" in element):
                    arguments  = self._map_properties_names(
                        {
                            "verify_md5": "data_update_verify_md5",
                            "data_file_update_base_url": "data_update_url"
                        },
                        element["elementParameters"],
                    )

                    flow_element = flow_element(**arguments)
                else:
                    flow_element = flow_element()
                flow_elements.append(flow_element)

            return Pipeline(flow_elements, suppress_process_exceptions=self._get_suppress_process_exceptions(config), auto_close_elements=self.auto_close_elements)
        except BaseException:
            # A failure to close is logged rather than raised, so the caller
            # sees the error that stopped the build.
            for flow_element in flow_elements:
                close = getattr(flow_element, "close", None)
                if close is None:
                    continue
                try:
                    close()
                except Exception as e:
                    self.logger.log(
                        "error",
                        "Could not close {} after the pipeline failed to "
                        "build: {}".format(type(flow_element).__name__, e))
            raise

    def _get_suppress_process_exceptions(self, config):
        """
        Resolve the suppress_process_exceptions setting from a configuration.
        Looks under 'PipelineOptions.BuildParameters' (mirrors the .NET/Java
        config layout for cross-language consistency), then a direct
        'PipelineOptions' key, accepting either snake_case or camelCase, and
        finally falls back to the value supplied to the builder constructor
        (default False).

        @type config: dict
        @param config: pipeline configuration
        @rtype: bool
        @return: whether processing exceptions should be suppressed
        """

        options = config.get("PipelineOptions", {})

        def lookup(source):
            if not isinstance(source, dict):
                return None
            for key in ("suppress_process_exceptions", "suppressProcessExceptions"):
                if key in source:
                    return source[key]
            return None

        value = lookup(options.get("BuildParameters"))
        if value is None:
            value = lookup(options)
        if value is None:
            return self.suppress_process_exceptions

        return value

    def _map_properties_names(self, mappings, arguments):
        if arguments is None:
            return arguments

        return dict(
            map(
                lambda key: (mappings[key], arguments[key]) if key in mappings else (key, arguments[key]),
                arguments
            )
        )

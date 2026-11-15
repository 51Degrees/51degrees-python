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

from types import MappingProxyType

from .evidence_keyfilter import EvidenceKeyFilter
from .flowdata import FlowData
from .logger import Logger


class PipelineEvidenceKeyFilter(EvidenceKeyFilter):

    """!
    The Evidence a Pipeline accepts, being every key one of its FlowElements
    accepts. Each element's filter is read when a key is checked, as an
    element's list can change once its data or the cloud service's answer
    arrives.

    """

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def filter_evidence_key(self, key):
        return any(
            element.get_evidence_key_filter().filter_evidence_key(key)
            for element in self.pipeline.flow_elements_list.values())


class Pipeline:

    """!
    Pipeline holding a list of FlowElements for processing,
    can create FlowData that will be passed through these,
    collecting ElementData
    Should be constructed through the PipelineBuilder class

    A Pipeline cannot be changed once it is built. flow_elements and
    flow_elements_display_list are tuples, and flow_elements_list, the
    elements by data key, is a read-only mapping. Each is a property with
    no setter. Code can read them, and adding, removing or replacing an
    element, or binding one of them again, raises an error.

    """

    def __init__(self, flow_elements, logger=Logger(), suppress_process_exceptions = False, data_file_update_service = None, auto_close_elements = True):

        """!
        Pipeline constructor.

        @type flow_elements: list[FlowElement]
        @param flow_elements: The flowElements, in the order they run. The
        pipeline keeps a copy, so changing this list afterwards changes
        nothing.

        @type logger: Logger
        @param logger: A logger to attach to the pipeline

        @type suppress_process_exceptions: boolean
        @param suppress_process_exceptions: If true then pipeline will suppress 
        exceptions added to FlowData.errors otherwise will throw the exception
        occurred during the processing of first element.

        @type auto_close_elements: boolean
        @param auto_close_elements: If true, the default, closing the
        pipeline closes its flow elements. Set it to false when the elements
        are shared with another pipeline, and close each element once every
        pipeline using it is finished with.

        @rtype: Pipeline
        @return: Returns a Pipeline

        """

        self._flow_elements = tuple(flow_elements)

        self.logger = logger

        # Filled below as each element is registered, so an element finds
        # those registered before it, and read only through this view.
        elements_by_key = {}
        self._flow_elements_list = MappingProxyType(elements_by_key)

        self._flow_elements_display_list = ()

        self.suppress_process_exceptions = suppress_process_exceptions

        self.auto_close_elements = auto_close_elements
  
        if data_file_update_service != None:
            self.data_file_update_service = data_file_update_service
            self.data_file_update_service.register_pipeline(self)
      
        for flow_element in self._flow_elements:

            # Notify element that it has been registered in the pipeline
            flow_element.on_registration(self)

            elements_by_key[flow_element.datakey] = flow_element

            flow_element.pipelines.append(self)

            if not flow_element.exclude_from_messages:
                self._flow_elements_display_list += (flow_element.datakey,)

    @property
    def flow_elements(self):
        """!
        The FlowElements, in the order they run, as a tuple.
        """
        return self._flow_elements

    @property
    def flow_elements_list(self):
        """!
        The FlowElements by data key, as a read-only mapping.
        """
        return self._flow_elements_list

    @property
    def flow_elements_display_list(self):
        """!
        The data keys named in messages, as a tuple.
        """
        return self._flow_elements_display_list

    def create_flowdata(self):

        """!
        Create a FlowData based on what's in the pipeline
        
        @rtype: FlowData
        @return: Return a FlowData

        """

        return FlowData(self)

    def close(self):

        """!
        Close the flow elements, which releases the native data they hold
        and stops the updates of their data files, unless the pipeline was
        built with auto_close_elements set to false. Use a with statement
        so that this happens when the pipeline is finished with.

        FlowData created by the pipeline are not closed by it. Close each
        one as well, because the results it holds keep the engine's data in
        memory until they are released.

        @raise Exception: the first error a flow element raised when it was
        closed, once every element has been closed

        """

        if not self.auto_close_elements:
            return

        # Every element is closed even if one fails, and the first failure
        # is raised once they all have been.
        failure = None
        for flow_element in self.flow_elements:
            close = getattr(flow_element, "close", None)
            if close is None:
                continue
            try:
                close()
            except Exception as e:
                if failure is None:
                    failure = e
        if failure is not None:
            raise failure

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def log(self, level, message):

        """!
        Log a message using the Logger.log of the pipeline's Logger.

        @type level: string
        @param level: level of log message

        @type message: string
        @param message: Returns content of log message

        """

        self.logger.log(level, message)

    def get_element(self, key):

        """!
        Get a flowElement by its name.

        @type key: string
        @param key: name of flowElement

        @rtype: FlowElement
        @return: Returns the FlowElement indicated

        """

        return self.flow_elements_list[key]

    def get_evidence_key_filter(self):

        """!
        The Evidence the Pipeline accepts, being every key one of its
        FlowElements accepts.

        @rtype: EvidenceKeyFilter
        @return: Returns an EvidenceKeyFilter

        """

        return PipelineEvidenceKeyFilter(self)

    def element_not_found(self, element, flowdata):
        """!
        Trigger error when an element cannot be found in the pipeline

        @type element: string
        @param element: name of flowelement 
        @type flowdata: flowdata
        @param element: flowdata being processsed 
        @raise Exception: always, naming the keys the FlowData does hold

        """

        # A list, so the keys are shown in square brackets.
        raise Exception(
            "There is no element data for " + element + " against this "
            "flow data. Available element data keys are: " +
            str(list(flowdata.pipeline.flow_elements_display_list)))


    def get_properties(self):

        """!
        Get all properties of all flowElements in the pipeline.

        @rtype: dict of {string : DataPropertyDictionary}
        @return: Returns dictionary of all properties in a pipeline keyed by each flowElement's FlowElement.datakey.

        """

        output = {}

        for flow_element in self.flow_elements:
            properties = flow_element.get_properties()

            output[flow_element.datakey] = properties

        return output

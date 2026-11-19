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

from .elementdata import ElementData
from .evidence import Evidence
from .flowerror import FlowError
from .messages import Messages
import traceback
import sys


def _set_finished(element_data, finished):

    # Records whether the FlowElement that writes the data has finished, which
    # ElementData checks before a write. Data of another type is left alone.
    if isinstance(element_data, ElementData):
        object.__setattr__(element_data, "_finished", finished)


def _give_back(element_data):

    # Gives the data back to the pool of the FlowElement that made it, if
    # that element keeps one. An element that is not a FlowElement has no
    # get_element_data_pool and keeps no pool.
    if isinstance(element_data, ElementData):
        flow_element = element_data.__dict__.get("flow_element")
        get_pool = getattr(flow_element, "get_element_data_pool", None)
        pool = get_pool() if callable(get_pool) else None
        if pool is not None:
            pool.give_back(element_data)


class FlowData:
    """!
    FlowData is created by a specific Pipeline
    It collects evidence set by the user
    It passes evidence to FlowElements in the Pipeline
    These elements can return ElementData or populate an errors object

    """

    def __init__(self, pipeline):

        """!
        FlowData constructor.

        @type pipeline: Pipeline
        @param pipeline: parent pipeline

        """

        self.data = {}
        self.errors = {}
        self.pipeline = pipeline
        self.processed = False
        self.stopped = False
        self.evidence = Evidence(self)
        # Set by close(), so that a second call gives nothing back again.
        self._closed = False

    def process(self):

        """!
        Runs the process function on every attached flowElement allowing data to be changed based on evidence.
        This can only be run once per FlowData instance.

        @rtype: FlowData
        @return: Returns flowdata
        @raise Exception: the first error a flow element raised, unless the
        Pipeline suppresses process exceptions, and every error is in errors
        either way. A second call raises the error saying this FlowData has
        already been processed, as a finished FlowData takes no more errors.

        """

        # A finished FlowData takes no more errors, so a second call raises.
        if self.processed:
            raise Exception(Messages.FLOW_DATA_PROCESSED)

        # filter evidence before processing
        try:
            self.evidence.filter()
        except Exception as e:
            flow_error = FlowError("global", e, traceback.format_exc())
            self.set_error(flow_error)

        for flow_element in self.pipeline.flow_elements:
            if self.stopped is not True:
                key = str(flow_element.datakey).lower()
                # A FlowElement that shares data another added may write it
                # again while it processes.
                _set_finished(self.data.get(key), False)
                # All errors are caught and stored in an errors array keyed by the
                # flowElement that set the error
                try:
                    flow_element.process(self)
                except Exception:
                    flow_error = FlowError(flow_element.datakey, sys.exc_info()[1], traceback.format_exc())
                    self.set_error(flow_error)
                finally:
                    _set_finished(self.data.get(key), True)

        # Data added before processing, or under another FlowElement's key,
        # is finished too.
        for element_data in list(self.data.values()):
            _set_finished(element_data, True)

        # Set processed flag to true. flowdata can only be processed once,
        # and is read only from now on.
        self.processed = True

        if self.errors and self.pipeline.suppress_process_exceptions is False:
            errored_flow_element_key = next(iter(self.errors))
            flowErrorObj = self.errors[errored_flow_element_key]             
            raise flowErrorObj.exception_instance 

        return self

    def close(self):

        """!
        Release the native resources held by the element data in this
        FlowData, such as the results of an on-premise engine, which keep
        the engine's data in memory until they are released. Use a with
        statement so that this happens as soon as the FlowData is finished
        with, rather than when the garbage collector next runs.

        Only element data with a close method of its own is closed, so
        element data that needs no cleanup, such as an entry in a results
        cache, is left alone. Values already read are unaffected.

        Each element data is then given back to the ElementDataPool of the
        FlowElement that made it, if that element keeps one, for a later
        request to reuse. So keeping a reference to element data after its
        FlowData is closed is not supported, because another request may
        then change its values. Reads are not checked for this. Data a
        cache may hold is never given back. A second call does nothing.

        """

        if self._closed:
            return
        self._closed = True

        given_back = set()
        for element_data in list(self.data.values()):
            # Data held under two keys is closed and given back once.
            if id(element_data) in given_back:
                continue
            given_back.add(id(element_data))
            # Looked up on the class, because ElementData treats an
            # attribute it does not have as the name of a property.
            close = getattr(type(element_data), "close", None)
            if callable(close):
                # Releasing what the data holds is not a write to it.
                finished = (isinstance(element_data, ElementData)
                            and element_data._finished)
                _set_finished(element_data, False)
                try:
                    close(element_data)
                finally:
                    _set_finished(element_data, finished)
            # Given back only once its close has returned. Data whose close
            # waits for a lazy task still writing it so goes back only after
            # that task has finished, which the specification requires.
            _give_back(element_data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def get_from_element(self, flow_element):

        """!
        Retrieve data by FlowElement object.

        @type flow_element: FlowElement
        @param flow_element: FlowElement that created the data of interest

        @rtype: ElementData
        @return: Returns data that was created by the flowElement held in the FlowData

        """

        try:
            return self.get(flow_element.datakey)

        except Exception:
            return None


    def get(self, flow_element_key):

        """!
        Retrieve data by flowElement key.
        Called by FlowData.get_from_element method.

        @type flow_element_key: string
        @param flow_element_key: FlowElement.datakey of the FlowElement that created the data of interest

        @rtype: ElementData
        @return: Returns data in the FlowData instance that is under the specified key
        @raise Exception: where this FlowData holds no data under the
        key, with a message naming the keys it does hold

        """

        try:
            return self.data[flow_element_key.lower()]

        except Exception:

            return self.pipeline.element_not_found(flow_element_key, self)

    def __getattr__(self, flow_element_key):

        """!
        Magic getter to allow retrieval of data from FlowData.data[flowElementKey] by flowElement name.
        For example, instead of `flowdata.get("device")` you can use `flowdata.device`

        @type flow_element_key: string
        @param flow_element_key: datakey of the FlowElement that created the data of interest

        @rtype: ElementData
        @raise Exception: where this FlowData holds no data under the
        key, with a message naming the keys it does hold
        
        """

        return self.get(flow_element_key)

    def __getitem__(self, flow_element_key):

        """!
        Magic method in Python, which when used in a class, allows its instances to use the [] (indexer) operators.
        For example, instead of `flowdata.get("device")` you can use `flowdata["device"]`

        @type flow_element_key: string
        @param flow_element_key: datakey of the FlowElement that created the data of interest

        @rtype: ElementData
        @raise Exception: where this FlowData holds no data under the
        key, with a message naming the keys it does hold
        
        """

        return self.get(flow_element_key)
		
    def set_element_data(self, element_data):

        """!
        Set data (used by flowElement) within FlowData.data

        @type element_data: ElementData
        @param element_data: elementData to be added to flowdata
        @raise Exception: once this FlowData has finished processing

        """

        if self.processed:
            raise Exception(Messages.FLOW_DATA_FINISHED.format("ElementData"))

        # Kept under the data key in lower case, which is how get reads it.
        self.data[element_data.flow_element.datakey.lower()] = element_data


    def set_error(self, flow_error):
    
        """!
        Set error (should be keyed by flowElement datakey)

        @type error: FlowError
        @param error: Flow Error
        @raise Exception: once this FlowData has finished processing

        """

        if self.processed:
            raise Exception(Messages.FLOW_DATA_FINISHED.format("an error"))

        self.errors[flow_error.flow_element] = flow_error

        log_message = "Error occurred during processing"

        if flow_error.flow_element:
            
            log_message = log_message + " of " + flow_error.flow_element + ". \n" + flow_error.exception_traceback

        self.pipeline.log("error", log_message)


    def get_evidence_datakey(self):
        """!
        Get a list of evidence stored in the flowdata, filtered by
        its flowElements' evidenceKeyFilters

        @rtype: list
        @return: Returns filtered evidence
        """
        # TODO: Research and fix this method. It is probably not working as expected.
        #   Temp. fix is introduced at the end of this method.

        # requestedEvidence = list()
        #
        # for flow_element in self.pipeline.flow_elements:
        #     requested_evidence = requestedEvidence.extend(flow_element.filter_evidence(self))
        #
        # return requested_evidence
        return [fe.filter_evidence(self) for fe in self.pipeline.flow_elements]

    def stop(self):

        """!
        Stop processing any subsequent flowElements
        @return void
        
        """

        self.stopped = True

    def get_where(self, metakey, metavalue):

        """!
        Get data from flowElement based on property meta data

        @type metakey: str
        @param metakey: metakey shared by all data of interest

        @type metavalue: mixed
        @param metavalue: meta value shared by all data of interest

        @rtype: dict
        @return: Returns dictionary of data created by the flowElement that have the specified meta property

        """

        meta_query_output = {}

        properties = self.pipeline.get_properties()

        for flow_element, flow_element_properties in properties.items():
            for propertykey, propertymeta in flow_element_properties.items():
                if metakey.lower() in propertymeta:
                    if propertymeta[metakey.lower()] == metavalue:
                        try:
                            meta_query_output[propertykey] = self.get(flow_element).get(propertykey)                
                        # We are ignoring errors in getWhere as properties could be missing on purpose
                        # They shouldn't throw an error breaking the whole getWhere.
                        except Exception:
                            pass
                        
        return meta_query_output
                        

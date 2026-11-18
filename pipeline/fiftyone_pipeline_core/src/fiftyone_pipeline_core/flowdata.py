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

from .evidence import Evidence
from .flowerror import FlowError
from .messages import Messages	
import traceback
import sys
from collections.abc import MutableMapping


def _find(node, key):

    # Follows the links from the node given to the first, so newest, node
    # for the key.
    while node is not None:
        if node.key == key:
            return node
        node = node.next
    return None


class _ElementDataNode(object):

    """!
    One Element Data in a FlowData's list. A node never changes once it is
    in the list, so a reader follows the links with no lock.
    """

    __slots__ = ("key", "element_data", "next")

    def __init__(self, key, element_data, next):
        self.key = key
        self.element_data = element_data
        self.next = next


class ElementDataView(MutableMapping):

    """!
    The Element Data of a FlowData, keyed by data key, as the list was when
    the view was taken. Adds made elsewhere after that are not seen, so a
    reader part way through always sees a whole list.

    Setting a key adds to the FlowData, and this view then shows the list
    as it is after the add. Element Data is not removed, so del, pop,
    popitem and clear raise TypeError. copy gives a dict.

    Iteration gives each key once, in the order the keys were first added.
    While a Pipeline processes, each Flow Element adds its own in turn, so
    that is Pipeline order. Element Data added another way, such as before
    processing, is listed by when it was added.
    """

    def __init__(self, flowdata, head):
        self._flowdata = flowdata
        self._head = head

    def _latest(self):
        # The list holds the newest first, so it is sorted into the order
        # the keys were added, keeping the newest Element Data for each.
        nodes = []
        node = self._head
        while node is not None:
            nodes.append(node)
            node = node.next
        latest = {}
        for node in reversed(nodes):
            latest[node.key] = node.element_data
        return latest

    def __getitem__(self, key):
        node = _find(self._head, key)
        if node is None:
            raise KeyError(key)
        return node.element_data

    def __setitem__(self, key, element_data):
        self._flowdata._add(key, element_data)
        # This view now shows the list with the add, as a mapping should.
        self._head = self._flowdata._head

    def __delitem__(self, key):
        raise TypeError("Element Data is not removed from a FlowData")

    def __iter__(self):
        return iter(self._latest())

    def __len__(self):
        return len(self._latest())

    def __repr__(self):
        return repr(self._latest())

    def copy(self):
        return self._latest()

    def keys(self):
        return self._latest().keys()

    def values(self):
        return self._latest().values()

    def items(self):
        return self._latest().items()


class FlowData:
    """!
    FlowData is created by a specific Pipeline
    It collects evidence set by the user
    It passes evidence to FlowElements in the Pipeline
    These elements can return ElementData or populate an errors object

    The Element Data is kept in a linked list, newest first. An add puts a
    new node at the head with a plain write and takes no lock, because no
    parallel group adds at the same time. Readers follow the links with no
    lock.

    A FlowData is not safe to use from several threads at once. The caller
    is responsible for any locking.

    """

    def __init__(self, pipeline):

        """!
        FlowData constructor.

        @type pipeline: Pipeline
        @param pipeline: parent pipeline

        """

        # The newest node of the Element Data list. See data.
        self._head = None
        self.errors = {}
        self.pipeline = pipeline
        self.processed = False
        self.stopped = False
        self.evidence = Evidence(self)

    def process(self):

        """!
        Runs the process function on every attached flowElement allowing data to be changed based on evidence.
        This can only be run once per FlowData instance.

        @rtype: FlowData
        @return: Returns flowdata
        @raise Exception: the first error a flow element raised, or the
        error saying this FlowData has already been processed, unless the
        Pipeline suppresses process exceptions. Every error is in errors
        either way.

        """

        if not self.processed:
            # filter evidence before processing
            try:
                self.evidence.filter()
            except Exception as e:
                flow_error = FlowError("global", e, traceback.format_exc())
                self.set_error(flow_error)

            for flow_element in self.pipeline.flow_elements:
                if self.stopped is not True:
                    # All errors are caught and stored in an errors array keyed by the
                    # flowElement that set the error
                    try:
                        flow_element.process(self)
                    except Exception:
                        flow_error = FlowError(flow_element.datakey, sys.exc_info()[1], traceback.format_exc())
                        self.set_error(flow_error)

            # Set processed flag to true. flowdata can only be processed once
            self.processed = True
        else:
            flow_error = FlowError("global", Exception(Messages.FLOW_DATA_PROCESSED), Messages.FLOW_DATA_PROCESSED)
            self.set_error(flow_error)

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

        """

        for element_data in list(self.data.values()):
            # Looked up on the class, because ElementData treats an
            # attribute it does not have as the name of a property.
            close = getattr(type(element_data), "close", None)
            if callable(close):
                close(element_data)

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
            node = _find(self._head, flow_element_key.lower())
        except Exception:
            node = None

        if node is None:
            return self.pipeline.element_not_found(flow_element_key, self)

        return node.element_data

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

        """

        # Kept under the data key in lower case, which is how get reads it.
        self._add(element_data.flow_element.datakey.lower(), element_data)

    def _add(self, key, element_data):

        # A new node at the head. A reader that has already read the head
        # keeps the list it saw.
        self._write_head(_ElementDataNode(key, element_data, self._head))

    def _write_head(self, head):

        # The only write of the list, with a plain write, as no parallel
        # group adds at the same time.
        self._head = head

    @property
    def data(self):

        """!
        The Element Data in this FlowData, keyed by data key in lower case,
        as the list is now. Iteration gives Pipeline order.

        @rtype: ElementDataView
        """

        return ElementDataView(self, self._head)

    @data.setter
    def data(self, contents):

        # Replaces the list with the contents given, in their order. The
        # new list is built first and put in place with one write, so a
        # reader sees the old list or the new one. The mapping given is
        # copied, so later changes to it are not seen.
        head = None
        for key, element_data in contents.items():
            head = _ElementDataNode(key, element_data, head)
        self._write_head(head)


    def set_error(self, flow_error):
    
        """!
        Set error (should be keyed by flowElement datakey)

        @type error: FlowError
        @param error: Flow Error

        """

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
                        

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

from .messages import Messages


class _CheckedDictWrites(object):

    """!
    The write methods of a dict, each of which calls _check_writable first,
    so a dict that holds Element Data values refuses writes once the
    FlowElement that writes them has finished. Reads are the dict's own.
    """

    __slots__ = ()

    def __setitem__(self, key, value):
        self._check_writable(key)
        super(_CheckedDictWrites, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._check_writable(key)
        super(_CheckedDictWrites, self).__delitem__(key)

    def __ior__(self, other):
        self._check_writable("|=")
        return super(_CheckedDictWrites, self).__ior__(other)

    def update(self, *args, **kwargs):
        self._check_writable("update")
        super(_CheckedDictWrites, self).update(*args, **kwargs)

    def pop(self, *args):
        self._check_writable(args[0] if args else "pop")
        return super(_CheckedDictWrites, self).pop(*args)

    def popitem(self):
        self._check_writable("popitem")
        return super(_CheckedDictWrites, self).popitem()

    def setdefault(self, key, default=None):
        self._check_writable(key)
        return super(_CheckedDictWrites, self).setdefault(key, default)

    def clear(self):
        self._check_writable("clear")
        super(_CheckedDictWrites, self).clear()


class _ContentsDict(_CheckedDictWrites, dict):

    """!
    The contents of Element Data that keeps its values in a dict. A write
    raises once the FlowElement that writes the data has finished, as a
    write to the data itself does. A copy is a plain dict.
    """

    __slots__ = ("_owner",)

    def __init__(self, owner, values):
        dict.__init__(self, values)
        self._owner = owner

    def _check_writable(self, name):
        self._owner._check_writable(name)

    def __reduce_ex__(self, protocol):
        return (dict, (dict(self),))


def _get_contents(data):
    return data.__dict__.get("_contents")


def _set_contents(data, values):
    data._contents = _ContentsDict(data, values)


# The contents property of the Element Data classes that keep their values
# in a dict. Setting it keeps a copy, which refuses writes once finished.
_contents_property = property(
    _get_contents, _set_contents,
    doc="The values, keyed by property name. Written only while the "
        "FlowElement that provides the data processes.")


class ElementData(object):

    """!
    Core ElementData class
    Stores information created by a FlowElement based on FlowData.
    Stored in FlowData

    Only the Flow Element that creates an instance writes it, so an instance
    does not need to be safe to write from several threads. A finished
    instance, once the Flow Element that writes it has finished, is safe to
    read from several threads at once, such as the caller's own threads. An
    instance that is written from several threads, or read while another
    thread writes it, is not catered for.

    A FlowElement may take its instances from an ElementDataPool, and
    closing the FlowData gives them back for a later request to reuse. So
    keeping a reference to ElementData after its FlowData is closed is not
    supported, because another request may then change its values. Reads
    are not checked for this.

    """

    def __init__(self, flow_element):

        """!
        Constructor for ElementData

        @type flow_element: FlowElement
        @param flow_element: FlowElement that data has been created by

        """

        self.flow_element = flow_element

    # Set once the FlowElement that writes the data has finished processing,
    # and cleared while one that shares the instance processes. A class
    # default, so data whose constructor does not call this one has it too.
    _finished = False

    def __setattr__(self, name, value):

        """!
        Set an attribute, unless the FlowElement that writes the data has
        finished processing, when a public attribute cannot be set. Names
        starting with an underscore hold the data's own state, such as
        values kept once read, and are not writes.

        @raise Exception: when the FlowElement has finished processing
        """

        if self._finished and not name.startswith("_"):
            self._raise_finished(name)
        object.__setattr__(self, name, value)

    def _check_writable(self, name):

        """!
        Raise unless the FlowElement that writes the data is processing. A
        write method calls this first.

        @type name: str
        @param name: what is being written, for the message
        @raise Exception: when the FlowElement has finished processing
        """

        if self._finished:
            self._raise_finished(name)

    def _raise_finished(self, name):
        flow_element = self.__dict__.get("flow_element")
        key = getattr(flow_element, "datakey", "")
        raise Exception(Messages.ELEMENT_DATA_FINISHED.format(name, key))

    def _clear(self):

        """!
        Ready an instance taken from an ElementDataPool for a new request,
        open for writing. A class with values of its own overrides this to
        drop them as well, so that none of the last request's remain.
        """

        self._finished = False

    def get(self, key):

        """!
        Get a value from the elementData contents
        Proxy for the ElementData.getInternal method

        @type key: str
        @param: key

        @rtype: mixed
        @return: Returns specified property from the data

        """

        return self.get_internal(key.lower())

    def __getattr__(self, key):

        """!
        Magic getter for a property from the data
        Allowing  user to write for example Data.IsMobile rather than Data.get("IsMobile)

        @type key: str
        @param key: property

        @rtype: mixed
        @return: Returns specified property from the data
        """

        return self.get(key)

    def __getitem__(self, flow_element_key):
    
        """!
        Magic method in Python, which when used in a class, allows its instances to use the [] (indexer) operators.
        For example, instead of `flowdata.get("device")` you can use `flowdata["device"]`

        @type flow_element_key: string
        @param flow_element_key: datakey of the FlowElement that created the data of interest

        @rtype: ElementData
        
        """

        return self.get(flow_element_key)
		
    def get_internal(self, key):
        
        """!
        Returns the requested property from the data
        Overridden by specific ElementData instances.

        @type key: str
        @param key: property

        @rtype: mixed
        @return: Returns Requested property from data
        """

        return

    def get_properties(self):

        """!
        Proxy to the data's flowElement properties.
        Gets the FlowElement.properties of the parent FlowElement.

        @rtype: DataPropertyDictionary
        @return: Returns dictionary of the parent FlowElement's properties
        """

        return self.flow_element.get_properties()

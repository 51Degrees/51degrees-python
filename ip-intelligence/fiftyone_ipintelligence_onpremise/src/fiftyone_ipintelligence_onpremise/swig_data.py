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

from fiftyone_pipeline_engines.aspectdata import AspectData
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

from fiftyone_pipeline_engines.missingproperty_service import MissingPropertyService

from .constants import RESULTS_CLOSED

# Latitude and Longitude are given to this many decimal places, as the
# native code gives them in text and in the WKT of Areas.
COORDINATE_DECIMAL_PLACES = 3

COORDINATE_PROPERTIES = ("latitude", "longitude")


class OnPremiseMissingPropertyService(MissingPropertyService):

    def check(self, key, flow_element):

        if key in flow_element.properties:
            datafiles = flow_element.properties[key]["datafiles"]
            if(not flow_element.engine.getProduct() in datafiles):
                raise Exception('Property ' + key + ' not found in data for element ' + flow_element.datakey + '. This is because your datafile does not contain the property. The property is available in' + str(datafiles))
        else:
            raise Exception('Property ' + key + ' not found in data for element ' + flow_element.datakey + '. Please check that the element and property names are correct.')


class SwigData(AspectData):

    """!
    Extension of AspectData made for retrieving results
    created by the SWIG wrapper of the On Premise IP Intelligence engine
    """

    def __init__(self, flow_element, swig_results, echo_ip=None, echo_ipv6=None):

        """!
        Constructor for swig_data
        @type flow_element: FlowElement
        @param flow_element: FlowElement / Engine the data is keyed under
        @type swig_results: ResultsIpiSwig
        @param swig_results: Results from the SWIG wrapper's process method
        @type echo_ip: string
        @param echo_ip: the IPv4 address found in evidence (or None)
        @type echo_ipv6: string
        @param echo_ipv6: the IPv6 address found in evidence (or None)
        """

        super(SwigData, self).__init__(flow_element)

        self.swig_results = swig_results
        self.echo_ip = echo_ip
        self.echo_ipv6 = echo_ipv6

        self.missing_property_service = OnPremiseMissingPropertyService()

    def close(self):

        """!
        Release the native results, which keep the engine's data in memory
        while they are held, even after the engine is closed. Values already
        read are unaffected, and reading a property afterwards raises an
        exception. Closing the FlowData closes its results.
        """

        self.swig_results = None

    def get(self, key):

        """!
        Get a property value, once the results are known to be open
        @type key: string
        @param key: The key of the property to retrieve
        @returns mixed
        """

        # Checked here, because AspectData.get turns an exception from
        # get_internal into a missing property message.
        if self.swig_results is None:
            raise Exception(RESULTS_CLOSED)

        return super(SwigData, self).get(key)

    @staticmethod
    def utf8_string_to_str(utf8_string):

        """!
        Convert a SWIG wrapped std::vector<uint8_t> UTF-8 string to a
        python string
        """

        return bytes(utf8_string).decode("utf-8", "replace")

    def weighted_list_to_value(self, value, convert=None):

        """!
        Convert a SWIG wrapped weighted value list to a list of
        {"value": ..., "weighting": ...} dictionaries wrapped in an
        AspectPropertyValue. This matches the shape of weighted values
        returned by the cloud engine.
        """

        if not value.hasValue():
            return AspectPropertyValue(no_value_message=value.getNoValueMessage())

        items = []

        # SWIG returns the wrapped std::vector of weighted values as a
        # python sequence
        for weighted_value in value.getValue():
            raw_value = weighted_value.getValue()
            if convert:
                raw_value = convert(raw_value)
            items.append({
                "value": raw_value,
                "weighting": weighted_value.getWeight()
            })

        return AspectPropertyValue(value=items)

    def ip_address_value(self, value):

        """!
        Convert a SWIG wrapped Value<IpAddress> to an AspectPropertyValue
        holding the IP address as a string.
        """

        import ipaddress

        from .IpIntelligenceEngineModule import (
            FIFTYONE_DEGREES_IP_TYPE_IPV4,
            FIFTYONE_DEGREES_IP_TYPE_IPV6)

        if not value.hasValue():
            return AspectPropertyValue(no_value_message=value.getNoValueMessage())

        ip = value.getValue()
        buffer = bytearray(16)
        ip.getCopyOfIpAddress(buffer, len(buffer))

        ip_type = ip.getType()

        if ip_type == FIFTYONE_DEGREES_IP_TYPE_IPV4:
            return AspectPropertyValue(value=str(ipaddress.IPv4Address(bytes(buffer[:4]))))
        if ip_type == FIFTYONE_DEGREES_IP_TYPE_IPV6:
            return AspectPropertyValue(value=str(ipaddress.IPv6Address(bytes(buffer[:16]))))

        return AspectPropertyValue(no_value_message="The IP address type is invalid.")

    @staticmethod
    def round_coordinate(value):

        """!
        A latitude or longitude to COORDINATE_DECIMAL_PLACES places
        """

        return round(value, COORDINATE_DECIMAL_PLACES)

    def single_value(self, value, convert=None):

        """!
        Convert a SWIG wrapped Value to an AspectPropertyValue holding
        the value (or the no value message).
        """

        if not value.hasValue():
            return AspectPropertyValue(no_value_message=value.getNoValueMessage())

        raw_value = value.getValue()
        if convert:
            raw_value = convert(raw_value)

        return AspectPropertyValue(value=raw_value)

    def get_internal(self, key):

        """!
        Get property values out of the SWIG wrapper
        @type key: string
        @param key: The key of the property to retrieve
        @returns mixed
        """

        # Lowercase key

        key = key.lower()

        # Start with the special echo properties. The IP address supplied
        # in evidence is echoed back in the results.

        if key == "ip":
            if self.echo_ip:
                return AspectPropertyValue(value=self.echo_ip)
            return AspectPropertyValue(no_value_message="IPv4 was not supplied as evidence.")

        if key == "ipv6":
            if self.echo_ipv6:
                return AspectPropertyValue(value=self.echo_ipv6)
            return AspectPropertyValue(no_value_message="IPv6 was not supplied as evidence.")

        # End special properties

        this_property = self.flow_element.properties[key]

        if this_property:

            results = self.swig_results
            name = this_property["name"]
            property_type = this_property["type"].lower()

            # Mcc is weighted even though its metadata type is "string"
            # (ip-intelligence-dotnet parity).

            if property_type == "string" and name.lower() == "mcc":
                property_type = "weightedstring"

            if property_type in ("weightedstring", "weightedwkbr", "weightedwkb"):
                return self.weighted_list_to_value(
                    results.getValuesAsWeightedUTF8StringList(name),
                    convert=self.utf8_string_to_str)

            if property_type == "weightedint":
                return self.weighted_list_to_value(
                    results.getValuesAsWeightedIntegerList(name))

            # Only the coordinates are rounded.
            round_coordinate = (
                self.round_coordinate if name.lower() in COORDINATE_PROPERTIES
                else None)

            if property_type in ("weighteddouble", "weightedsingle"):
                return self.weighted_list_to_value(
                    results.getValuesAsWeightedDoubleList(name),
                    convert=round_coordinate)

            if property_type == "weightedbool":
                return self.weighted_list_to_value(
                    results.getValuesAsWeightedBoolList(name))

            if property_type in ("wkb", "wkbr"):
                # WKB geometry properties (e.g. Areas) are exposed as their
                # WKT string form. getValueAsString returns the WKT directly,
                # matching the .NET binding. The weighted-WKT list getter
                # (getValuesAsWeightedWKTStringList) is not used as it is not
                # safely exposed through the Python SWIG wrapper.
                return self.single_value(results.getValueAsString(name))

            if property_type == "ipaddress":
                # IP address properties (e.g. IpRangeStart / IpRangeEnd) are
                # read as their string form. This matches the .NET binding,
                # which reads IP properties via getValueAsString rather than
                # the lower-level getValueAsIpAddress accessor.
                return self.single_value(results.getValueAsString(name))

            if property_type in ("string", "javascript"):
                return self.single_value(
                    results.getValueAsUTF8String(name),
                    convert=self.utf8_string_to_str)

            if property_type == "int":
                return self.single_value(results.getValueAsInteger(name))

            if property_type in ("double", "single"):
                return self.single_value(
                    results.getValueAsDouble(name), convert=round_coordinate)

            if property_type == "bool":
                return self.single_value(results.getValueAsBool(name))

            if property_type == "string[]":
                value = results.getValues(name)
                if value.hasValue():
                    return AspectPropertyValue(value=list(value.getValue()))
                return AspectPropertyValue(no_value_message=value.getNoValueMessage())

            # Unknown type, fall back to string

            return self.single_value(results.getValueAsString(name))

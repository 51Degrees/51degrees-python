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

from fiftyone_pipeline_engines.missingproperty_service import \
    OnPremiseMissingPropertyService

from .constants import RESULTS_CLOSED

# The names of the C library's match methods, in the order of its
# fiftyoneDegreesHashMatchMethod values, which getMethod returns.
MATCH_METHODS = ("NONE", "PERFORMANCE", "COMBINED", "PREDICTIVE")


class SwigData(AspectData):

    """!
    Extention of AspectData made for retrieving results
    created by the SWIG wrapper of the On Premise Device Detection engine

    An instance reads its values from a results instance, the native results
    of one request, which holds unmanaged memory. Multi-threaded access to a
    results instance is not supported, for performance reasons, so an
    instance is not safe to use from several threads at once. The caller is
    responsible for thread-safe access, and either gives each thread its own
    Flow Data, and so its own results instance, or coordinates its own
    access, for example with a lock of its own around every read and around
    close().
    """

    def __init__(self, flow_element, swig_results):
        
        """!
        Constructor for swig_data
        @type flow_element: FlowElement
        @param flow_element: FlowElement / Engine the data is keyed under
        @type swig_results: ResultsHashSwig
        @param swig_results: Results from the SWIG wrapper's process method
        """

        super(SwigData, self).__init__(flow_element)

        self.swig_results = swig_results

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

    def get_internal(self, key):

        """!
        Get property values out of the SWIG wrapper
        @type key: string
        @param key: The key of the property to retrieve
        @returns mixed
        """

        #   start with special properties

        # Lowercase key

        key = key.lower()

        if key == "deviceid":
            return AspectPropertyValue(value = self.swig_results.getDeviceId())

        if key == 'useragents':
            # Populated only when the engine records the matched
            # User-Agents, as its default is an empty list.
            if not getattr(self.flow_element, "update_matched_useragent", True):
                return AspectPropertyValue(value = [])
            # Each component's result has a matched User-Agent, and several
            # can match the same one, which is listed once.
            useragents = []
            for i in range(self.swig_results.getUserAgents()):
                useragent = self.swig_results.getUserAgent(i)
                if useragent not in useragents:
                    useragents.append(useragent)
            return AspectPropertyValue(value = useragents)

        if key == 'difference':
            return AspectPropertyValue(value = self.swig_results.getDifference())

        if key == 'method':
            method = self.swig_results.getMethod()
            return AspectPropertyValue(
                value = MATCH_METHODS[method]
                if 0 <= method < len(MATCH_METHODS) else "NONE")

        if key == 'matchednodes':
            return AspectPropertyValue(value = self.swig_results.getMatchedNodes())

        if key == 'drift':
            return AspectPropertyValue(value = self.swig_results.getDrift())

        if key == 'iterations':
            return AspectPropertyValue(value = self.swig_results.getIterations())
            
        # End special properties

        this_property = self.flow_element.properties[key]

        if this_property:

            value = None

            # Read by the property's index from the engine's build-time
            # table. A name outside the table is read by name, which gives
            # the native no value message.
            target = getattr(self.flow_element, "property_indexes", {}).get(
                key, this_property["name"])

            if this_property["type"] == "bool":
                value = self.swig_results.getValueAsBool(target)

            if this_property["type"] == "string":
                value = self.swig_results.getValueAsString(target)

            if this_property["type"] == "javascript":
                value = self.swig_results.getValueAsString(target)
            
            if this_property["type"] == "int":
                value = self.swig_results.getValueAsInteger(target)

            if this_property["type"] == "double":
                value = self.swig_results.getValueAsDouble(target)

            if this_property["type"] == "string[]":
                value = self.swig_results.getValues(target)
   

            # Check for value / no value message

            if value.hasValue():
                
                # Convert value to list if needed
                if this_property["type"] == 'string[]':
                    return AspectPropertyValue(value=list(value.getValue()))

                return AspectPropertyValue(value=value.getValue())
            
            else:

                return AspectPropertyValue(no_value_message=value.getNoValueMessage())

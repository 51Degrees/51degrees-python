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

from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary

from fiftyone_pipeline_engines.missingproperty_service import \
    MissingPropertyReason, MissingPropertyService


class CloudMissingPropertyService(MissingPropertyService):

    """!
    The missing property service of a Cloud Aspect Engine. A property its
    metadata does not list is one the key in use does not include, or,
    while the engine's property list is not known, one whose request for
    that list failed.
    """

    def engine_reason(self, flow_element):

        """!
        The reason for a property the metadata does not list.

        @type flow_element: CloudEngine
        @param flow_element: the engine
        @rtype: tuple
        @return: the reason, and the property names the key includes
        """

        properties_known = getattr(flow_element, "properties_known", None)
        if properties_known is not None and not properties_known():
            # The Cloud Request Engine asks for the property list when it is
            # built, so a list that is still not known is one whose request
            # failed.
            return MissingPropertyReason.CLOUD_REQUEST_FAILED, ()
        properties = self.properties(flow_element)
        if not properties:
            return (
                MissingPropertyReason.PRODUCT_NOT_ACCESSIBLE_WITH_RESOURCE_KEY,
                ())
        return (
            MissingPropertyReason.PROPERTY_NOT_ACCESSIBLE_WITH_RESOURCE_KEY,
            [meta.get("name", name) for name, meta in properties.items()])


# The name this service had before, kept for code that imports it.
OnPremiseMissingPropertyService = CloudMissingPropertyService

class CloudData(AspectDataDictionary):

    """!
    Extention of AspectData made for retrieving cloud engine results
    """

    def __init__(self, flow_element, contents):
        
        """!
        Constructor for cloud_data
        @type flow_element: FlowElement
        @param flow_element: FlowElement / Engine the data is keyed under
        @type contents: dict
        @param contents: Results from cloud engine's process method
        """

        super(CloudData, self).__init__(flow_element, contents)

        self.missing_property_service = CloudMissingPropertyService()

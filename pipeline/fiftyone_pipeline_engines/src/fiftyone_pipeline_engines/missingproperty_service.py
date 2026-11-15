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

from enum import Enum


class MissingPropertyReason(Enum):
    """!
    Why a property an engine defines is missing from its data, named as the
    .NET packages name each reason.
    """

    DATA_FILE_UPGRADE_REQUIRED = "DataFileUpgradeRequired"
    PROPERTY_EXCLUDED_FROM_ENGINE_CONFIGURATION = \
        "PropertyExcludedFromEngineConfiguration"
    PRODUCT_NOT_ACCESSIBLE_WITH_RESOURCE_KEY = \
        "ProductNotAccessibleWithResourceKey"
    PROPERTY_NOT_ACCESSIBLE_WITH_RESOURCE_KEY = \
        "PropertyNotAccessibleWithResourceKey"
    CLOUD_REQUEST_FAILED = "CloudRequestFailed"
    UNKNOWN = "Unknown"


# The pages the messages link to, with this repository's campaign
# parameters.
PRICING_URL = (
    "https://51degrees.com/pricing?utm_source=code&utm_medium=comment"
    "&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-"
    "src-fiftyone_pipeline_engines-missingproperty_service.py"
    "&utm_term=missing-property-pricing")
CONFIGURATOR_URL = (
    "https://configure.51degrees.com/?utm_source=code&utm_medium=comment"
    "&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-"
    "src-fiftyone_pipeline_engines-missingproperty_service.py"
    "&utm_term=missing-property-configurator")

# Lists in a message are joined with a comma and no space.
LIST_SEPARATOR = ","


def missing_property_message(
        reason, name, element, tiers=(), engine_type="", properties=()):
    """!
    The message of the missing properties table for a reason.

    @type reason: MissingPropertyReason
    @param reason: why the property is missing
    @type name: str
    @param name: the property, as the caller named it
    @type element: str
    @param element: the data key of the element asked
    @type tiers: list
    @param tiers: the data tiers that hold the property, for
    DATA_FILE_UPGRADE_REQUIRED, where an empty list gives the row for
    tiers that are not known
    @type engine_type: str
    @param engine_type: the engine's type name, for
    DATA_FILE_UPGRADE_REQUIRED
    @type properties: list
    @param properties: the property names the key includes, for
    PROPERTY_NOT_ACCESSIBLE_WITH_RESOURCE_KEY
    @rtype: str
    @return: the message
    """

    text = ("Property '" + name + "' not found in data for element '" +
            element + "'. ")
    if reason is MissingPropertyReason.DATA_FILE_UPGRADE_REQUIRED:
        text += ("This is because your license or data file does not "
                 "include this property. ")
        if tiers:
            return text + (
                "It is available with the " + LIST_SEPARATOR.join(tiers) +
                " license/data for the " + engine_type +
                ". To upgrade, see " + PRICING_URL + ".")
        return text + (
            "To see which licenses include it, see " + PRICING_URL + ".")
    if reason is MissingPropertyReason.PROPERTY_EXCLUDED_FROM_ENGINE_CONFIGURATION:
        return text + ("This is because the property has been excluded "
                       "when configuring the engine.")
    if reason is MissingPropertyReason.PRODUCT_NOT_ACCESSIBLE_WITH_RESOURCE_KEY:
        return text + (
            "This is because your resource key does not include access to "
            "any properties under '" + element + "'. Check or create a "
            "resource key with the properties you need in the configurator "
            "at " + CONFIGURATOR_URL + ".")
    if reason is MissingPropertyReason.PROPERTY_NOT_ACCESSIBLE_WITH_RESOURCE_KEY:
        return text + (
            "This is because your resource key does not include access to "
            "this property. The properties included for your key under '" +
            element + "' are " + LIST_SEPARATOR.join(properties) +
            ". Check or change your key in the configurator at " +
            CONFIGURATOR_URL + ".")
    if reason is MissingPropertyReason.CLOUD_REQUEST_FAILED:
        return text + (
            "This is because an upstream cloud request failed, so no data "
            "was available to populate the property.")
    return text + ("The reason for this is unknown. Please check that the "
                   "aspect and property name are correct.")


class MissingPropertyService():

    """!
    Raises the error for a property an engine's data does not hold, giving
    the reason in the order the properties specification sets out, with
    the missing properties table's message for it. Property names are
    compared ignoring case. Engines of a kind override needs_upgrade and
    engine_reason to add their own steps.
    """

    def check(self, key, flow_element):

        """!
        Raise the error for a property the data has no value for.

        @type key: string
        @param key: the property asked for
        @type flow_element: FlowElement
        @param flow_element: the element whose data was asked
        @raise Exception: always, with the message for the reason the
        property is missing
        """

        raise Exception(self.message(key, flow_element))

    def message(self, key, flow_element):

        """!
        The message for the reason a property is missing.

        @type key: string
        @param key: the property asked for
        @type flow_element: FlowElement
        @param flow_element: the element whose data was asked
        @rtype: str
        @return: the message
        """

        name = key.lower()
        listed = None
        for property_name, meta in self.properties(flow_element).items():
            if property_name.lower() == name:
                listed = meta
                break
        restricted = getattr(flow_element, "restricted_property_keys", None)

        # A property the metadata lists, or one the restricted list leaves
        # out, is in a data tier the data file does not hold, or was
        # excluded.
        if listed is not None or (
                restricted is not None and name not in restricted):
            tiers = list((listed or {}).get("datafiles") or ())
            if listed is not None and self.needs_upgrade(tiers, flow_element):
                return missing_property_message(
                    MissingPropertyReason.DATA_FILE_UPGRADE_REQUIRED, key,
                    flow_element.datakey, tiers=tiers,
                    engine_type=type(flow_element).__name__)
            return missing_property_message(
                MissingPropertyReason.PROPERTY_EXCLUDED_FROM_ENGINE_CONFIGURATION,
                key, flow_element.datakey)

        reason, properties = self.engine_reason(flow_element)
        return missing_property_message(
            reason, key, flow_element.datakey, properties=properties)

    def properties(self, flow_element):

        """!
        The engine's property metadata, by name.

        @type flow_element: FlowElement
        @param flow_element: the engine
        @rtype: dict
        @return: the metadata of each property, by name
        """

        get_properties = getattr(flow_element, "get_properties", None)
        if get_properties is not None:
            return get_properties() or {}
        return getattr(flow_element, "properties", None) or {}

    def needs_upgrade(self, tiers, flow_element):

        """!
        Whether a property the metadata lists is missing because the
        engine's data file is not of one of the property's tiers. An engine
        with no data file never needs an upgrade.

        @type tiers: list
        @param tiers: the data tiers that hold the property
        @type flow_element: FlowElement
        @param flow_element: the engine
        @rtype: bool
        @return: True where an upgrade is needed
        """

        return False

    def engine_reason(self, flow_element):

        """!
        The reason for a property the metadata does not list, which a kind
        of engine with a step of its own overrides.

        @type flow_element: FlowElement
        @param flow_element: the engine
        @rtype: tuple
        @return: the reason, and the property names for a message that
        lists them
        """

        return MissingPropertyReason.UNKNOWN, ()


class OnPremiseMissingPropertyService(MissingPropertyService):

    """!
    The missing property service of an on-premise engine, whose data file
    tier decides whether a property the metadata lists needs an upgrade.
    The engine's native engine gives the tier.
    """

    def needs_upgrade(self, tiers, flow_element):

        """!
        Whether the tier of the data file the engine uses is not among a
        property's tiers.

        @type tiers: list
        @param tiers: the data tiers that hold the property
        @type flow_element: FlowElement
        @param flow_element: the engine
        @rtype: bool
        @return: True where an upgrade is needed
        """

        return flow_element.engine.getProduct() not in tiers

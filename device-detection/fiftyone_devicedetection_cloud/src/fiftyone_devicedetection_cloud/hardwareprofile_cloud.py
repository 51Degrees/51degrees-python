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

from __future__ import absolute_import
from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.clouddata import \
    CloudMissingPropertyService

from fiftyone_pipeline_engines.aspectdata import AspectData
from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

import json

# The suffix the cloud service adds to a property name to carry the reason
# that property has no value, for example "hardwarevendornullreason".
NULL_REASON_SUFFIX = "nullreason"

# The key the cloud request engine's data is read under, and the old key,
# which is deprecated. An older cloud request engine gives the old key
# alone.
RESPONSE_DATA_KEY = "cloud-response"
OLD_DATA_KEY = "cloud"


def _cloud_response(flowdata):
    """!
    The raw JSON the cloud request engine gave, read under cloud-response,
    or under the old key when there is nothing under cloud-response.

    @rtype string
    @return the JSON text of the cloud service's answer
    """

    try:
        data = flowdata.get(RESPONSE_DATA_KEY)
    except Exception:
        data = None
    if data is None:
        data = flowdata.get(OLD_DATA_KEY)
    return data.get("cloud")


class HardwareProfileData(dict, AspectData):
    """!
    One hardware profile from a profile lookup, read in the way the device
    data is read. It is Aspect Data, so a property is read as an attribute,
    such as profile.hardwarevendor, with get() or with [].

    It is also a dict of property name to AspectPropertyValue. Iteration,
    len and keys() give the names the cloud service gave, and get() takes a
    default as a dict's get() does.
    Attribute access, get(), [] and in compare names ignoring letter case.
    A property whose name is also a dict method, such as keys, is read
    with get() or [].
    """

    # Attributes set in the constructor, which are never read as properties.
    _OWN_ATTRIBUTES = ("flow_element", "missing_property_service")

    def __init__(self, flow_element, contents):
        """!
        @type flow_element: HardwareProfileCloud
        @param flow_element: the engine that made the profile

        @type contents: dict
        @param contents: property name to AspectPropertyValue
        """

        dict.__init__(self, contents)
        AspectData.__init__(self, flow_element)

        # The device data's service, so a name that is not a property is
        # reported in the same way for both.
        self.missing_property_service = CloudMissingPropertyService()

    def _matching_key(self, key):
        """!
        The key held for a property name given in another letter case, or
        None when there is none.
        """

        if isinstance(key, str):
            lowered = key.lower()
            for held in dict.keys(self):
                if isinstance(held, str) and held.lower() == lowered:
                    return held
        return None

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            held = self._matching_key(key)
            if held is None:
                raise
            return dict.__getitem__(self, held)

    def __contains__(self, key):
        return (dict.__contains__(self, key)
                or self._matching_key(key) is not None)

    def get(self, key, default=None):
        """!
        The value of a property by name in any letter case, or default when
        the profile does not hold it, as a dict gives.
        """

        try:
            return self[key]
        except KeyError:
            return default

    def get_internal(self, key):
        """!
        The value of a property by name in any letter case, or None when the
        profile does not hold it, which AspectData.get() reports as missing.
        """

        return self.get(key)

    def as_dictionary(self):
        """!
        The profile itself, being a dict of property name to value.
        """

        return self

    def __getattr__(self, name):
        """!
        Read a property as an attribute. Python calls this only for a name
        the profile does not otherwise have. A name that is not a property
        raises AttributeError with the device data's message, so hasattr()
        and getattr() with a default work.
        """

        # Names that start with an underscore, such as the special methods
        # copy and pickle look for, are never properties. Reading the
        # profile's own attributes as properties would recurse.
        if name.startswith("_") or name in self._OWN_ATTRIBUTES:
            raise AttributeError(name)
        try:
            return AspectData.get(self, name)
        except Exception as error:
            raise AttributeError(str(error)) from error

    def __reduce__(self):
        # A copy or a pickle of a profile is a plain dict of its values,
        # because the engine a profile refers to holds a lock, which cannot
        # be copied or pickled.
        return (dict, (dict(self),))


def _build_aspect_values(hardware):
    """!
    Build the aspect level property values from the "hardware" section of a
    cloud response, pairing each null value with the reason the service gave
    for it.

    @type hardware: dict
    @param hardware: the "hardware" section of the cloud response

    @rtype dict
    @return property name to AspectPropertyValue
    """

    values = {}

    for key, value in hardware.items():
        if key == "profiles" or key.endswith(NULL_REASON_SUFFIX):
            continue

        if value is None:
            reason = hardware.get(key + NULL_REASON_SUFFIX)
            values[key] = AspectPropertyValue(
                no_value_message=reason if isinstance(reason, str) else None)
        else:
            values[key] = AspectPropertyValue(value=value)

    return values


class HardwareProfileCloud(CloudEngine):
    """!
    The hardware profile cloud engine
    """
    def __init__(self):

        super(HardwareProfileCloud, self).__init__()

        self.datakey = "hardware"

    def process_internal(self, flowdata):

        cloud_data = json.loads(_cloud_response(flowdata))

        hardware = cloud_data.get("hardware") or {}

        if not isinstance(hardware, dict):
            hardware = {}

        # Properties the resource key is not entitled to are returned by the
        # cloud service at the aspect level rather than inside each profile,
        # with a companion "<name>nullreason" saying why there is no value.
        # Collect those so the reason can travel with every profile instead
        # of being thrown away.
        aspect_values = _build_aspect_values(hardware)

        devices = []

        for profile in hardware.get("profiles") or []:
            device = {}
            for property_key, property_value in profile.items():
                device[property_key] = AspectPropertyValue(value=property_value)

            # Add the properties the service could not supply, carrying the
            # reason it gave, so a caller reading a profile gets an
            # explanation rather than nothing at all.
            for property_key, aspect_value in aspect_values.items():
                if property_key not in device:
                    device[property_key] = aspect_value

            devices.append(HardwareProfileData(self, device))

        # The aspect level values are exposed alongside the profiles so a
        # caller with no matching profiles can still read the reason.
        contents = dict(aspect_values)
        contents["profiles"] = devices

        data = AspectDataDictionary(self, contents)

        flowdata.set_element_data(data)
        
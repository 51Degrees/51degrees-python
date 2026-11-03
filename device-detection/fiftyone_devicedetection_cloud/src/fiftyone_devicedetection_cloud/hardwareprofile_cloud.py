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

from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

import json

# The suffix the cloud service adds to a property name to carry the reason
# that property has no value, for example "hardwarevendornullreason".
NULL_REASON_SUFFIX = "nullreason"


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

        cloud_data = flowdata.get("cloud").get("cloud")

        cloud_data = json.loads(cloud_data)

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

            devices.append(device)

        # The aspect level values are exposed alongside the profiles so a
        # caller with no matching profiles can still read the reason.
        contents = dict(aspect_values)
        contents["profiles"] = devices

        data = AspectDataDictionary(self, contents)

        flowdata.set_element_data(data)
        
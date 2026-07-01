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
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

# The cloud sends weighted values with a raw 16-bit weighting ("rawweighting",
# 0-65535, the same field ip-intelligence-dotnet reads into IWeightedValue.
# RawWeighting). The rest of this SDK - and the on-premise engine's getWeight()
# - expresses weighting as a 0.0-1.0 proportion, so normalise by the maximum.
_RAW_WEIGHTING_MAX = 65535


class IpIntelligenceCloud(CloudEngine):
    """!
    The IP Intelligence cloud engine requires the 51Degrees
    cloudRequestEngine to be placed in a pipeline before it.
    It takes that raw JSON response and parses it to extract the
    IP intelligence part. It also uses this data to generate a list
    of properties. Weighted properties (e.g. Mcc) are returned as
    lists of {"value": ..., "weighting": ...} dictionaries, where the
    cloud's raw 0-65535 weighting is normalised to a 0.0-1.0 proportion
    so it matches the on-premise engine.
    """
    def __init__(self):

        super(IpIntelligenceCloud, self).__init__()

        self.datakey = "ip"

    def process_internal(self, flowdata):

        """!
        Parse the cloud response via the base engine, then normalise the
        weighted values so their shape matches the on-premise engine
        ({"value", "weighting"} with weighting as a 0.0-1.0 proportion).
        """

        super(IpIntelligenceCloud, self).process_internal(flowdata)

        element_data = flowdata.get(self.datakey)

        weighted_keys = {
            name.lower()
            for name, meta in self.properties.items()
            if "weighted" in str(meta.get("type", "")).lower()
        }

        for key in weighted_keys:
            value = element_data.contents.get(key)
            if value is None or not value.has_value():
                continue
            items = value.value()
            if not isinstance(items, list):
                continue
            element_data.contents[key] = AspectPropertyValue(
                value=[self._normalise_weighting(item) for item in items])

    @staticmethod
    def _normalise_weighting(item):

        """Convert a single cloud weighted entry, turning the raw 0-65535
        "rawweighting" field into a 0.0-1.0 "weighting". Entries that already
        use "weighting" (or are not dictionaries) are left untouched."""

        if not isinstance(item, dict) or "rawweighting" not in item:
            return item
        normalised = dict(item)
        normalised["weighting"] = (
            normalised.pop("rawweighting") / float(_RAW_WEIGHTING_MAX))
        return normalised

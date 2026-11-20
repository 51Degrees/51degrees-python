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

"""!
The base of the cloud engines whose section of the cloud response holds
weighted values.
"""

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

# The cloud gives each weighted value a raw weighting from 0 to 65535.
RAW_WEIGHTING_MAX = 65535


class WeightedCloudEngine(CloudEngine):
    """!
    A cloud engine whose section includes weighted values. The cloud sends
    each one as a list of {"value", "rawweighting"} entries, with the raw
    weighting from 0 to 65535. The engine gives each entry a "weighting"
    from 0.0 to 1.0 in place of the raw one, the form the on-premise
    engines use.
    """

    def process_internal(self, flowdata):

        super(WeightedCloudEngine, self).process_internal(flowdata)

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

        """!
        Give one weighted entry its weighting as a proportion. An entry that
        is not a dictionary, or has no raw weighting, is returned unchanged.
        """

        if not isinstance(item, dict) or "rawweighting" not in item:
            return item
        normalised = dict(item)
        normalised["weighting"] = (
            normalised.pop("rawweighting") / float(RAW_WEIGHTING_MAX))
        return normalised

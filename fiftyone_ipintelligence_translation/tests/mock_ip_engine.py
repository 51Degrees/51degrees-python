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

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue


class MockIpEngine(FlowElement):

    """!
    A mock IP Intelligence element. It exposes the weighted country code
    properties used by the translation engines under the "ip" element data key,
    so the engines can be tested in isolation, exactly as the .NET tests mock
    the IP element.
    """

    def __init__(self, geographic_codes, population_codes):
        super().__init__()
        self.datakey = "ip"
        self.properties = {
            "CountryCodesGeographical": {"type": "object"},
            "CountryCodesPopulation": {"type": "object"},
        }
        self._geographic = geographic_codes
        self._population = population_codes

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {
            "CountryCodesGeographical": AspectPropertyValue(
                value=self._geographic),
            "CountryCodesPopulation": AspectPropertyValue(
                value=self._population),
        }))
        return True


def weightify(country_codes):

    """!
    Turn a plain list of country codes into a weighted list, assigning
    descending weights by input order so the most probable country (the first)
    has the highest weight.
    """

    count = len(country_codes)
    return [
        {"value": code, "weighting": (count - index) / count}
        for index, code in enumerate(country_codes)
    ]


def mock_ip_element(geographic_codes, population_codes):

    """!
    Create a mock IP element from plain code lists, weighted by input order.
    """

    return MockIpEngine(
        weightify(geographic_codes), weightify(population_codes))


def mock_ip_element_weighted(geographic_codes, population_codes):

    """!
    Create a mock IP element from explicit weighted code lists. Each entry is a
    {"value", "weighting"} dictionary.
    """

    return MockIpEngine(geographic_codes, population_codes)

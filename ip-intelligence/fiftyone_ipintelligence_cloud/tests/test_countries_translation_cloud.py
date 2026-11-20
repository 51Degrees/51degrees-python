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

"""
The translated country names engine reads the "countrynamestranslated"
section of the cloud response, with no network and no resource key.
"""

import json
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import (
    CloudRequestEngine)

from fiftyone_ipintelligence_cloud.countries_translation_cloud import (
    CountriesTranslationCloud)
from fiftyone_ipintelligence_cloud.ipintelligence_cloud import (
    IpIntelligenceCloud)
from fiftyone_ipintelligence_cloud.weighted_cloud_engine import (
    WeightedCloudEngine)

from .classes.mockrequestclient import MockRequestClient

DATA_KEY = "countrynamestranslated"

# The cloud gives each weighted value a raw weighting from 0 to 65535.
RAW_WEIGHTING_MAX = 65535

# What the cloud service says a key carrying the ip and the translated
# country names products can read.
ACCESSIBLE_PROPERTIES = {
    "Products": {
        "ip": {
            "DataTier": "CloudV5Bespoke",
            "Properties": [
                {"Name": "RegisteredName", "Type": "String",
                 "Category": "IP Metrics"},
                {"Name": "CountryCodesGeographical",
                 "Type": "WeightedString", "Category": "Location"},
            ]
        },
        DATA_KEY: {
            "DataTier": "CloudV5Bespoke",
            "Properties": [
                {"Name": "CountryNamesGeographicalTranslated",
                 "Type": "WeightedString", "Category": "Location"},
                {"Name": "CountryCodesGeographicalAll", "Type": "Array",
                 "Category": "Location"},
                {"Name": "CountryNamesGeographicalAllTranslated",
                 "Type": "Array", "Category": "Location"},
                {"Name": "SortingCultureUsed", "Type": "String",
                 "Category": "Location"},
            ]
        }
    }
}

# The cloud's answer for an address most likely in the United Kingdom, with
# the names in French.
RESULTS = {
    "ip": {
        "registeredname": "51 Degrees Mobile Experts Limited",
        "countrycodesgeographical": [
            {"rawweighting": 49151, "value": "GB"},
            {"rawweighting": 16384, "value": "IE"},
        ],
    },
    DATA_KEY: {
        "countrynamesgeographicaltranslated": [
            {"rawweighting": 49151, "value": "Royaume-Uni"},
            {"rawweighting": 16384, "value": "Irlande"},
        ],
        "countrycodesgeographicalall": ["GB", "IE", "ZA", "DE"],
        "countrynamesgeographicalalltranslated": [
            "Royaume-Uni", "Irlande", "Afrique du Sud", "Allemagne"],
        "sortingcultureused": "fr-FR",
    },
    "javascriptProperties": [],
}


class TranslatedRequestClient(MockRequestClient):
    """
    Answers as the cloud service does for a key carrying the ip and the
    translated country names products.
    """

    def request(self, type, url, content, originHeader):
        response = super().request(type, url, content, originHeader)
        if "accessibleProperties" in url:
            response.text = json.dumps(ACCESSIBLE_PROPERTIES)
        elif ".json" in url:
            response.text = json.dumps(RESULTS)
        else:
            return response
        response.content = response.text.encode("utf-8")
        return response


def build_pipeline():
    return (PipelineBuilder()
        .add(CloudRequestEngine({
            "resource_key": "resource_key",
            "http_client": TranslatedRequestClient()}))
        .add(IpIntelligenceCloud())
        .add(CountriesTranslationCloud())
        .build())


def process(pipeline):
    flowdata = pipeline.create_flowdata()
    flowdata.evidence.add("query.client-ip-51d", "185.28.167.78")
    flowdata.evidence.add("header.accept-language", "fr-FR")
    flowdata.process()
    return flowdata


class CountriesTranslationCloudTests(unittest.TestCase):

    def test_reads_the_translated_country_names_section(self):
        """
        The engine's data key is the cloud section's, which is also the
        on-premise countries translation engine's, so its results are in
        flowdata.countrynamestranslated either way.
        """

        self.assertEqual(CountriesTranslationCloud().datakey, DATA_KEY)
        self.assertEqual(CountriesTranslationCloud.DATA_KEY, DATA_KEY)

    def test_properties_come_from_the_product_the_key_carries(self):

        engine = build_pipeline().flow_elements_list[DATA_KEY]

        self.assertEqual(
            sorted(engine.properties),
            sorted(p["Name"]
                   for p in ACCESSIBLE_PROPERTIES["Products"][DATA_KEY][
                       "Properties"]))

    def test_weighted_names_carry_their_weighting_as_a_proportion(self):

        data = process(build_pipeline()).get(DATA_KEY)

        names = data.get("countrynamesgeographicaltranslated").value()

        self.assertEqual(
            [name["value"] for name in names], ["Royaume-Uni", "Irlande"])
        self.assertAlmostEqual(names[0]["weighting"], 49151 / RAW_WEIGHTING_MAX)
        self.assertAlmostEqual(names[1]["weighting"], 16384 / RAW_WEIGHTING_MAX)
        for name in names:
            self.assertNotIn("rawweighting", name)

    def test_the_all_lists_are_aligned_by_position(self):

        data = process(build_pipeline()).get(DATA_KEY)

        codes = data.get("countrycodesgeographicalall").value()
        names = data.get("countrynamesgeographicalalltranslated").value()

        self.assertEqual(codes, ["GB", "IE", "ZA", "DE"])
        self.assertEqual(
            names, ["Royaume-Uni", "Irlande", "Afrique du Sud", "Allemagne"])
        self.assertEqual(
            data.get("sortingcultureused").value(), "fr-FR")

    def test_ip_intelligence_results_are_unchanged(self):

        data = process(build_pipeline()).get("ip")

        codes = data.get("countrycodesgeographical").value()

        self.assertEqual([code["value"] for code in codes], ["GB", "IE"])
        self.assertAlmostEqual(codes[0]["weighting"], 49151 / RAW_WEIGHTING_MAX)
        self.assertEqual(
            data.get("registeredname").value(),
            "51 Degrees Mobile Experts Limited")

    def test_both_engines_share_one_weighting_conversion(self):
        """
        The weighted value conversion is written once, so the two engines
        cannot drift apart.
        """

        self.assertTrue(issubclass(IpIntelligenceCloud, WeightedCloudEngine))
        self.assertTrue(
            issubclass(CountriesTranslationCloud, WeightedCloudEngine))
        self.assertIs(
            CountriesTranslationCloud.process_internal,
            IpIntelligenceCloud.process_internal)


if __name__ == "__main__":
    unittest.main()

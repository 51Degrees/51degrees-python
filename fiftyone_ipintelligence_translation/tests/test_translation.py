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

import unittest

import yaml

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_translation.translator import Translator
from fiftyone_pipeline_translation.missing_translation_behavior import (
    MissingTranslationBehavior)

from fiftyone_ipintelligence_translation.country_code_translation_engine_builder import (
    CountryCodeTranslationEngineBuilder)
from fiftyone_ipintelligence_translation.countries_translation_engine_builder import (
    CountriesTranslationEngineBuilder)
from fiftyone_ipintelligence_translation.comparer import make_comparer
from fiftyone_ipintelligence_translation.resources import (
    get_all_countries, get_country_resources)

from .mock_ip_engine import (
    mock_ip_element, mock_ip_element_weighted, weightify)


def _build_pipeline(ip_element, translate_countries=True):
    builder = (PipelineBuilder()
               .add(ip_element)
               .add(CountryCodeTranslationEngineBuilder().build()))
    if translate_countries:
        builder = builder.add(CountriesTranslationEngineBuilder().build())
    return builder.build()


def _process(ip_element, evidence=None, translate_countries=True):
    pipeline = _build_pipeline(ip_element, translate_countries)
    flowdata = pipeline.create_flowdata()
    if evidence:
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
    flowdata.process()
    return flowdata


def _values(weighted_list):
    return [item["value"] for item in weighted_list]


def _comparer_for(translated_data):
    culture = translated_data.get("sortingcultureused")
    return make_comparer(culture or None)


def _assert_sorted(testcase, names, comparer, start=0):
    previous = None
    for name in names[start:]:
        key = comparer(name)
        if previous is not None:
            testcase.assertTrue(
                previous <= key,
                f"Expected '{previous}' <= '{key}'")
        previous = key


# ----------------------------------------------------------------------------
# 10a: ports of the current .NET coverage.
# ----------------------------------------------------------------------------

class CountryTranslationTests(unittest.TestCase):

    def test_country_names_from_codes(self):
        # Engine 1 alone: GB,FR -> United Kingdom, France (geo and pop).
        flowdata = _process(
            mock_ip_element(["GB", "FR"], ["GB", "FR"]),
            translate_countries=False)
        result = flowdata.get("countrynames")
        geo = result.get("CountryNamesGeographical")
        pop = result.get("CountryNamesPopulation")
        self.assertTrue(geo.has_value())
        self.assertTrue(pop.has_value())
        self.assertEqual(["United Kingdom", "France"], _values(geo.value()))
        self.assertEqual(["United Kingdom", "France"], _values(pop.value()))

    def test_translated_country(self):
        # Engines 1 and 2 with fr_FR: GB,FR -> Royaume-Uni, France.
        flowdata = _process(
            mock_ip_element(["GB", "FR"], ["GB", "FR"]),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        geo = result.get("CountryNamesGeographicalTranslated")
        self.assertTrue(geo.has_value())
        self.assertEqual(["Royaume-Uni", "France"], _values(geo.value()))

    def test_all_lists_produced_correctly_sorted(self):
        # Explicit weights (FR lower, GB higher), fr_FR: GB then FR first.
        geo = [
            {"value": "FR", "weighting": 0.30000},
            {"value": "GB", "weighting": 0.35535},
        ]
        flowdata = _process(
            mock_ip_element_weighted(list(geo), list(geo)),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")

        names_all = result.get("CountryNamesGeographicalAllTranslated")
        codes_all = result.get("CountryCodesGeographicalAll")
        self.assertTrue(names_all.has_value())
        self.assertTrue(codes_all.has_value())
        names = names_all.value()
        codes = codes_all.value()
        self.assertEqual(len(names), len(codes))

        self.assertEqual("Royaume-Uni", names[0])
        self.assertEqual("GB", codes[0])
        self.assertEqual("France", names[1])
        self.assertEqual("FR", codes[1])

        self.assertTrue(len(names) > 200)
        self.assertNotIn("GB", codes[2:])
        self.assertNotIn("FR", codes[2:])
        _assert_sorted(self, names, _comparer_for(result), start=2)

    def test_all_lists_produced_correctly(self):
        flowdata = _process(
            mock_ip_element(["GB", "FR"], ["GB", "FR"]),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertEqual(len(names), len(codes))
        self.assertEqual("Royaume-Uni", names[0])
        self.assertEqual("GB", codes[0])
        self.assertEqual("France", names[1])
        self.assertEqual("FR", codes[1])
        self.assertTrue(len(names) > 200)
        self.assertNotIn("GB", codes[2:])
        self.assertNotIn("FR", codes[2:])
        _assert_sorted(self, names, _comparer_for(result), start=2)

    def test_all_lists_without_language(self):
        flowdata = _process(mock_ip_element(["GB"], ["GB"]))
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertEqual("United Kingdom", names[0])
        self.assertEqual("GB", codes[0])
        self.assertTrue(len(names) > 200)
        _assert_sorted(self, names, _comparer_for(result), start=1)

    def test_all_lists_with_no_ip_data(self):
        flowdata = _process(
            mock_ip_element([], []),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertTrue(len(names) > 200)
        self.assertEqual(len(names), len(codes))
        _assert_sorted(self, names, _comparer_for(result))

    def test_all_lists_exclude_unknown_when_no_real_codes(self):
        flowdata = _process(
            mock_ip_element(["Unknown"], ["Unknown"]),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertTrue(len(codes) > 200)
        self.assertNotIn("Unknown", codes)
        self.assertNotIn("Unknown", names)
        _assert_sorted(self, names, _comparer_for(result))

    def test_all_lists_exclude_unknown_when_mixed_with_real_code(self):
        flowdata = _process(
            mock_ip_element(["DE", "Unknown"], ["DE", "Unknown"]),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertEqual("DE", codes[0])
        self.assertEqual("Deutschland", names[0])
        self.assertNotIn("Unknown", codes)
        self.assertNotIn("Unknown", names)
        self.assertEqual(len(names), len(codes))
        _assert_sorted(self, names, _comparer_for(result), start=1)

    def test_population_and_geographical_are_independent(self):
        flowdata = _process(
            mock_ip_element(["DE"], ["US", "CN"]))
        result = flowdata.get("countrynamestranslated")
        geo_codes = result.get("CountryCodesGeographicalAll").value()
        pop_codes = result.get("CountryCodesPopulationAll").value()

        self.assertEqual("DE", geo_codes[0])
        self.assertEqual("US", pop_codes[0])
        self.assertEqual("CN", pop_codes[1])
        self.assertNotEqual("DE", pop_codes[0])

    def test_german_translation(self):
        flowdata = _process(
            mock_ip_element(["DE"], ["DE"]),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")

        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Deutschland", translated[0]["value"])

        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()
        self.assertEqual("Deutschland", names[0])
        self.assertEqual("DE", codes[0])

    def test_accept_language_with_dash(self):
        flowdata = _process(
            mock_ip_element(["GB"], ["GB"]),
            {"header.accept-language": "fr-FR"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Royaume-Uni", translated[0]["value"])

    def test_english_language_no_translation(self):
        flowdata = _process(
            mock_ip_element(["FR", "DE"], ["FR", "DE"]),
            {"header.accept-language": "en-US,en;q=0.9"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("France", translated[0]["value"])
        self.assertEqual("Germany", translated[1]["value"])

        names = result.get("CountryNamesGeographicalAllTranslated").value()
        self.assertEqual("France", names[0])
        self.assertEqual("Germany", names[1])

    def test_english_preferred_over_other_languages(self):
        flowdata = _process(
            mock_ip_element(["DE"], ["DE"]),
            {"header.accept-language": "en-US,en;q=0.9,de-DE;q=0.5,fr;q=0.3"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Germany", translated[0]["value"])

    def test_preferred_language_matched_before_lower_priority(self):
        flowdata = _process(
            mock_ip_element(["DE"], ["DE"]),
            {"header.accept-language": "es,de-DE;q=0.8,fr;q=0.5"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Alemania", translated[0]["value"])


# ----------------------------------------------------------------------------
# 10b: gaps not covered by the current .NET tests.
# ----------------------------------------------------------------------------

class CountryTranslationGapTests(unittest.TestCase):

    def test_query_translation_evidence_key(self):
        # A bare query.translation = fr_FR translates to French.
        flowdata = _process(
            mock_ip_element(["GB"], ["GB"]),
            {"query.translation": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Royaume-Uni", translated[0]["value"])

    def test_query_translation_overrides_header(self):
        # query.translation has higher precedence than header.accept-language.
        flowdata = _process(
            mock_ip_element(["GB"], ["GB"]),
            {"query.translation": "fr_FR",
             "header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("Royaume-Uni", translated[0]["value"])
        self.assertEqual("fr-FR", result.get("sortingcultureused"))

    def test_weights_preserved_through_translation(self):
        geo = weightify(["GB", "FR"])
        flowdata = _process(
            mock_ip_element_weighted(list(geo), list(geo)),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        translated = result.get("CountryNamesGeographicalTranslated").value()

        self.assertEqual("Royaume-Uni", translated[0]["value"])
        self.assertEqual(geo[0]["weighting"], translated[0]["weighting"])
        self.assertEqual("France", translated[1]["value"])
        self.assertEqual(geo[1]["weighting"], translated[1]["weighting"])

    def test_equal_weight_tie_break(self):
        # Two countries with the same weight appear in translated-name order.
        geo = [
            {"value": "FR", "weighting": 0.5},
            {"value": "DE", "weighting": 0.5},
        ]
        flowdata = _process(
            mock_ip_element_weighted(list(geo), list(geo)),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        self.assertEqual({"DE", "FR"}, set(codes[:2]))
        comparer = _comparer_for(result)
        self.assertTrue(comparer(names[0]) <= comparer(names[1]))

    def test_unknown_locale_falls_back_to_english(self):
        flowdata = _process(
            mock_ip_element(["FR", "DE"], ["FR", "DE"]),
            {"header.accept-language": "zz-ZZ"})
        result = flowdata.get("countrynamestranslated")

        translated = result.get("CountryNamesGeographicalTranslated").value()
        self.assertEqual("France", translated[0]["value"])

        names_all = result.get("CountryNamesGeographicalAllTranslated")
        codes_all = result.get("CountryCodesGeographicalAll")
        self.assertTrue(names_all.has_value())
        self.assertTrue(codes_all.has_value())
        self.assertTrue(len(names_all.value()) > 200)
        self.assertEqual("", result.get("sortingcultureused"))

    def test_missing_single_name_stays_english(self):
        # The shipped data is complete, so use a small custom map. A known
        # English name absent from the locale map is returned unchanged.
        translator = Translator(
            {"Germany": "Allemagne"}, MissingTranslationBehavior.ORIGINAL)
        source = [
            {"value": "Germany", "weighting": 1.0},
            {"value": "Spain", "weighting": 0.5},
        ]
        result = translator.translate(source)
        self.assertEqual("Allemagne", result[0]["value"])
        self.assertEqual("Spain", result[1]["value"])

    def test_full_index_alignment(self):
        flowdata = _process(
            mock_ip_element(["DE", "FR"], ["DE", "FR"]),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        names = result.get("CountryNamesGeographicalAllTranslated").value()
        codes = result.get("CountryCodesGeographicalAll").value()

        code_to_english = {
            code.lower(): english for code, english in get_all_countries()}
        de_map = {
            str(key).lower(): value
            for key, value in yaml.safe_load(
                get_country_resources()["countries.de_DE.yml"]).items()}

        self.assertEqual(len(names), len(codes))
        for index, code in enumerate(codes):
            english = code_to_english[code.lower()]
            expected = de_map.get(english.lower(), english)
            self.assertEqual(
                expected, names[index],
                f"Misaligned at {index} for code '{code}'")

    def test_sorting_culture_used(self):
        french = _process(
            mock_ip_element(["GB"], ["GB"]),
            {"header.accept-language": "fr_FR"}).get("countrynamestranslated")
        self.assertEqual("fr-FR", french.get("sortingcultureused"))

        english = _process(
            mock_ip_element(["GB"], ["GB"]),
            {"header.accept-language": "en-US"}).get("countrynamestranslated")
        self.assertEqual("", english.get("sortingcultureused"))

        none = _process(
            mock_ip_element(["GB"], ["GB"])).get("countrynamestranslated")
        self.assertEqual("", none.get("sortingcultureused"))

    def test_country_code_no_is_not_coerced_to_false(self):
        # Regression: the ISO code "NO" (Norway) must survive YAML loading as
        # the string "NO", not the boolean False. safe_load's YAML 1.1 typing
        # turned it into False, so the code lists contained "False" and a
        # weighted "NO" from the IP engine was dropped as an unknown code.
        flowdata = _process(
            mock_ip_element([], []),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        codes = result.get("CountryCodesGeographicalAll").value()
        names = result.get("CountryNamesGeographicalAllTranslated").value()

        self.assertIn("NO", codes)
        self.assertNotIn("False", codes)
        self.assertEqual("Norvège", names[codes.index("NO")])

    def test_alphabetical_order_is_pinned(self):
        # The alphabetical remainder is asserted against literal expected
        # values rather than being re-checked with the engine's own comparer,
        # so a change in collation is caught instead of silently absorbed.
        flowdata = _process(
            mock_ip_element([], []),
            {"header.accept-language": "fr_FR"})
        result = flowdata.get("countrynamestranslated")
        codes = result.get("CountryCodesGeographicalAll").value()
        names = result.get("CountryNamesGeographicalAllTranslated").value()

        self.assertEqual(
            ["AF", "ZA", "AX", "AL", "DZ", "DE",
             "AO", "AI", "AQ", "AG", "SA", "AR"],
            codes[:12])
        self.assertEqual(
            ["Afghanistan", "Afrique du Sud", "Åland", "Albanie",
             "Algérie", "Allemagne", "Angola", "Anguilla", "Antarctique",
             "Antigua-et-Barbuda", "Arabie saoudite", "Argentine"],
            names[:12])

    def test_population_translated_names(self):
        flowdata = _process(
            mock_ip_element(["DE"], ["US", "CN"]),
            {"header.accept-language": "de_DE"})
        result = flowdata.get("countrynamestranslated")
        pop_names = result.get("CountryNamesPopulationAllTranslated").value()
        pop_codes = result.get("CountryCodesPopulationAll").value()

        self.assertEqual("US", pop_codes[0])
        self.assertEqual("Vereinigte Staaten von Amerika", pop_names[0])
        self.assertEqual("CN", pop_codes[1])
        # The population list differs from the geographical list.
        geo_codes = result.get("CountryCodesGeographicalAll").value()
        self.assertEqual("DE", geo_codes[0])
        self.assertNotEqual(geo_codes[0], pop_codes[0])


if __name__ == "__main__":
    unittest.main()

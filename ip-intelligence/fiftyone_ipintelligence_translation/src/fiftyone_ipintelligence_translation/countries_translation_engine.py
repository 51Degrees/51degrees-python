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

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_translation.translation_engine_base import (
    TranslationEngineBase)
from fiftyone_pipeline_translation.missing_translation_behavior import (
    MissingTranslationBehavior)

from .constants import Constants
from .comparer import make_comparer
from .resources import get_country_resources


class CountriesTranslationEngine(TranslationEngineBase):

    """!
    Engine which takes the English country name properties from the
    CountryCodeTranslationEngine and the weighted country code properties from
    the IP Intelligence engine, translates the country names to the browser
    language, and produces complete ordered lists of all countries combining the
    weighted results with all known countries.

    The base class handles the weighted translations
    (CountryNamesGeographical / Population to their Translated variants). This
    subclass adds the "All" list logic on top. Results are stored under the
    Constants.COUNTRY_NAMES_TRANSLATED_KEY element data key.
    """

    # Output properties added by this engine on top of the base translations.
    _EXTRA_PROPERTIES = [
        "CountryNamesGeographicalAllTranslated",
        "CountryNamesPopulationAllTranslated",
        "CountryCodesGeographicalAll",
        "CountryCodesPopulationAll",
        "SortingCultureUsed",
    ]

    def __init__(self, all_countries):

        """!
        Constructor.

        @type all_countries: list
        @param all_countries: Ordered list of (code, English name) pairs for
        every known country, as loaded from countrycodes.en_GB.yml.
        """

        super().__init__(
            # Source is the output of the CountryCodeTranslationEngine.
            Constants.COUNTRY_NAMES_KEY,
            [
                ("CountryNamesGeographical",
                 "CountryNamesGeographicalTranslated"),
                ("CountryNamesPopulation",
                 "CountryNamesPopulationTranslated"),
            ],
            get_country_resources(),
            None,
            MissingTranslationBehavior.ORIGINAL)

        self.datakey = Constants.COUNTRY_NAMES_TRANSLATED_KEY

        if all_countries is None:
            raise ValueError("all_countries must not be None.")
        self._all_countries = list(all_countries)
        # The set of real country codes, used to drop the IP engine's no-match
        # sentinel (e.g. "Unknown") from the "All" lists.
        self._valid_codes = {
            code.lower() for code, _name in self._all_countries}

        for name in self._EXTRA_PROPERTIES:
            self.properties[name] = {"type": "object"}

    def process_internal(self, flowdata):

        # Let the base class produce the weighted translated names.
        super().process_internal(flowdata)

        element_data = flowdata.get(self.datakey)

        # Resolve the translator and locale used for the "All" lists.
        translator, locale = self._resolve_translator(flowdata)
        culture_used = (
            locale.replace("_", "-")
            if translator is not None and locale else "")
        element_data.contents["sortingcultureused"] = culture_used
        comparer = make_comparer(culture_used or None)

        # Weighted codes come directly from the IP Intelligence element data.
        ip_data = self._get_ip_data(flowdata)
        geo_codes = self._weighted_list(ip_data, "CountryCodesGeographical")
        pop_codes = self._weighted_list(ip_data, "CountryCodesPopulation")

        # Weighted translated names come from the base class output.
        geo_names = self._weighted_list(
            element_data, "CountryNamesGeographicalTranslated")
        pop_names = self._weighted_list(
            element_data, "CountryNamesPopulationTranslated")

        self._build_and_store(
            element_data, geo_names, geo_codes, translator, comparer,
            "CountryNamesGeographicalAllTranslated",
            "CountryCodesGeographicalAll")
        self._build_and_store(
            element_data, pop_names, pop_codes, translator, comparer,
            "CountryNamesPopulationAllTranslated",
            "CountryCodesPopulationAll")

        return True

    @staticmethod
    def _get_ip_data(flowdata):
        try:
            return flowdata.get("ip")
        except Exception:
            return None

    @staticmethod
    def _weighted_list(data, property_name):

        """Return the list of weighted {"value", "weighting"} dictionaries for
        a property, or an empty list when it is missing or has no value."""

        if data is None:
            return []
        try:
            value = data.get(property_name)
        except Exception:
            return []
        if value is None:
            return []
        if isinstance(value, AspectPropertyValue):
            return value.value() if value.has_value() else []
        return value

    def _build_and_store(
            self, element_data, translated_names, weighted_codes, translator,
            comparer, names_property, codes_property):

        """Build the complete "All" lists for one dimension and store them in
        the element data."""

        # The weighted countries, most probable first. Keep only real country
        # codes so the IP engine's no-match sentinel never leads the list.
        weighted_tuples = [
            tuple_
            for tuple_ in self._build_weighted_tuples(
                translated_names, weighted_codes, comparer)
            if tuple_[0].lower() in self._valid_codes]

        used_codes = {code.lower() for code, _name in weighted_tuples}

        # Every remaining known country, alphabetical by translated name.
        remaining = [
            (code, english)
            for code, english in self._all_countries
            if code.lower() not in used_codes]
        if translator is not None:
            remaining = [
                (code, translator.translate(english) or english)
                for code, english in remaining]
        remaining.sort(key=lambda pair: comparer(pair[1]))

        all_tuples = weighted_tuples + remaining

        element_data.contents[codes_property.lower()] = AspectPropertyValue(
            value=[code for code, _name in all_tuples])
        element_data.contents[names_property.lower()] = AspectPropertyValue(
            value=[name for _code, name in all_tuples])

    @staticmethod
    def _build_weighted_tuples(translated_names, codes, comparer):

        """Zip the weighted translated names with the weighted codes by index,
        ordered by weighting descending then translated name ascending."""

        if not translated_names or not codes:
            return []
        count = min(len(translated_names), len(codes))
        tuples = []
        for index in range(count):
            name_item = translated_names[index]
            code_item = codes[index]
            tuples.append((
                code_item["value"],
                name_item["value"],
                name_item.get("weighting", 0)))
        tuples.sort(key=lambda item: (-item[2], comparer(item[1])))
        return [(code, name) for code, name, _weighting in tuples]

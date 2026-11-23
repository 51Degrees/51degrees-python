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

## @example onpremise/countries_pipeline.py
# @brief Shared helpers for the country translation examples.
#
# These helpers add the two country translation engines to a pipeline and
# build the HTML for the ordered country dropdown. They are kept separate from
# the runnable examples so they can be reused and tested without a data file.

import html

from fiftyone_ipintelligence_translation.country_code_translation_engine_builder import (
    CountryCodeTranslationEngineBuilder)
from fiftyone_ipintelligence_translation.countries_translation_engine_builder import (
    CountriesTranslationEngineBuilder)


def add_country_translation(builder):

    """!
    Add the two country translation engines to a pipeline builder, in order:
    the country code engine (codes to English names) followed by the countries
    engine (English names to the browser language plus the ordered "All"
    lists). The builder must already contain the on-premise IP Intelligence
    engine.

    @param builder: A pipeline builder to add the engines to.
    @return: The same builder, for chaining.
    """

    builder.add(CountryCodeTranslationEngineBuilder().build())
    builder.add(CountriesTranslationEngineBuilder().build())
    return builder


def build_country_options(codes, names):

    """!
    Build the index-aligned <option> elements for the country dropdown. Option
    i has the country code as its value and the translated country name as its
    text, most probable country first.

    @param codes: The ordered country codes (CountryCodesGeographicalAll).
    @param names: The ordered translated names
    (CountryNamesGeographicalAllTranslated).
    @return: A string of <option> elements.
    """

    options = []
    count = min(len(codes), len(names))
    for index in range(count):
        options.append(
            f'<option value="{html.escape(str(codes[index]))}">'
            f'{html.escape(str(names[index]))}</option>')
    return "\n".join(options)

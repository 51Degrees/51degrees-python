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

## @brief Tests for the country translation examples.
#
# The .NET examples only smoke-test the console examples (that they run without
# throwing) and the web example has no test at all. This asserts the ordering
# of the dropdown the examples produce: most probable country first, then every
# other country alphabetically. It uses a mock IP element so it runs without a
# data file.

import unittest

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from fiftyone_ipintelligence_examples.onpremise.countries_pipeline import (
    add_country_translation, build_country_options)


class _MockIpEngine(FlowElement):

    def __init__(self, geographic, population):
        super().__init__()
        self.datakey = "ip"
        self.properties = {
            "CountryCodesGeographical": {"type": "object"},
            "CountryCodesPopulation": {"type": "object"},
        }
        self._geographic = geographic
        self._population = population

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(self, {
            "CountryCodesGeographical": AspectPropertyValue(
                value=self._geographic),
            "CountryCodesPopulation": AspectPropertyValue(
                value=self._population),
        }))
        return True


class CountryTranslationExampleTests(unittest.TestCase):

    def _run(self):
        # GB weighted higher than FR, so GB must lead the ordered list.
        weighted = [
            {"value": "FR", "weighting": 0.30000},
            {"value": "GB", "weighting": 0.35535},
        ]
        builder = PipelineBuilder().add(
            _MockIpEngine(list(weighted), list(weighted)))
        add_country_translation(builder)
        pipeline = builder.build()

        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.translation", "fr_FR")
        flowdata.process()
        return flowdata.get("countrynamestranslated")

    def test_ordered_lists_most_probable_first(self):
        translated = self._run()
        codes = translated.get("CountryCodesGeographicalAll").value()
        names = translated.get("CountryNamesGeographicalAllTranslated").value()

        # Most probable first.
        self.assertEqual("GB", codes[0])
        self.assertEqual("Royaume-Uni", names[0])
        self.assertEqual("FR", codes[1])
        self.assertEqual("France", names[1])

        # Every known country is present, the two weighted ones only once.
        self.assertTrue(len(codes) > 200)
        self.assertEqual(len(codes), len(names))
        self.assertNotIn("GB", codes[2:])
        self.assertNotIn("FR", codes[2:])

    def test_build_country_options_index_aligned(self):
        translated = self._run()
        codes = translated.get("CountryCodesGeographicalAll").value()
        names = translated.get("CountryNamesGeographicalAllTranslated").value()
        options = build_country_options(codes, names)

        lines = options.splitlines()
        self.assertEqual(len(codes), len(lines))
        # First option is the most probable country.
        self.assertEqual(
            '<option value="GB">Royaume-Uni</option>', lines[0])
        self.assertEqual(
            '<option value="FR">France</option>', lines[1])

    def test_build_country_options_escapes(self):
        options = build_country_options(["X&Y"], ['a<b>"c'])
        self.assertEqual(
            '<option value="X&amp;Y">a&lt;b&gt;&quot;c</option>', options)


if __name__ == "__main__":
    unittest.main()

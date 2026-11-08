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
import warnings

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from fiftyone_pipeline_translation.translator import Translator
from fiftyone_pipeline_translation.languages import Languages
from fiftyone_pipeline_translation.missing_translation_behavior import (
    MissingTranslationBehavior)
from fiftyone_pipeline_translation.translation_engine_base import (
    TranslationEngineBase)


class MockSourceElement(FlowElement):

    """A flow element that exposes fixed values for testing the translation."""

    def __init__(self, datakey, contents):
        super().__init__()
        self.datakey = datakey
        self._contents = contents

    def process_internal(self, flowdata):
        flowdata.set_element_data(
            ElementDataDictionary(self, self._contents))
        return True


# A "fr_FR" style source file: English name -> French name.
FR_SOURCE = {
    "countries.fr_FR.yml": "Germany: Allemagne\nUnited Kingdom: Royaume-Uni\n"
}


class TranslatorTests(unittest.TestCase):

    def _translator(self, behavior=MissingTranslationBehavior.ORIGINAL):
        return Translator(
            {"Germany": "Allemagne", "United Kingdom": "Royaume-Uni"},
            behavior)

    def test_translate_string(self):
        self.assertEqual("Allemagne", self._translator().translate("Germany"))

    def test_translate_string_case_insensitive(self):
        self.assertEqual("Allemagne", self._translator().translate("germany"))

    def test_translate_list_of_strings(self):
        result = self._translator().translate(["Germany", "United Kingdom"])
        self.assertEqual(["Allemagne", "Royaume-Uni"], result)

    def test_translate_weighted_preserves_weighting(self):
        source = [
            {"value": "Germany", "weighting": 0.7},
            {"value": "United Kingdom", "weighting": 0.3},
        ]
        result = self._translator().translate(source)
        self.assertEqual("Allemagne", result[0]["value"])
        self.assertEqual(0.7, result[0]["weighting"])
        self.assertEqual("Royaume-Uni", result[1]["value"])
        self.assertEqual(0.3, result[1]["weighting"])

    def test_translate_aspect_property_value(self):
        wrapped = AspectPropertyValue(value=[
            {"value": "Germany", "weighting": 1.0}])
        result = self._translator().translate(wrapped)
        self.assertTrue(result.has_value())
        self.assertEqual("Allemagne", result.value()[0]["value"])

    def test_translate_aspect_property_value_no_value(self):
        wrapped = AspectPropertyValue(no_value_message="missing")
        result = self._translator().translate(wrapped)
        self.assertFalse(result.has_value())
        self.assertEqual("missing", result.no_value_message())

    def test_missing_original(self):
        self.assertEqual("Spain", self._translator().translate("Spain"))

    def test_missing_empty_string(self):
        translator = self._translator(MissingTranslationBehavior.EMPTY_STRING)
        self.assertEqual("", translator.translate("Spain"))

    def test_missing_flow_error(self):
        translator = self._translator(MissingTranslationBehavior.FLOW_ERROR)
        errors = []
        self.assertIsNone(translator.translate("Spain", errors))
        self.assertEqual(1, len(errors))


class LanguagesTests(unittest.TestCase):

    def test_parse_accept_language_orders_by_quality(self):
        result = Languages.parse_accept_language("es,de-DE;q=0.8,en;q=0.5")
        self.assertEqual(["es", "de_DE", "en"], result)

    def test_resolve_exact(self):
        self.assertEqual(
            "fr_FR",
            Languages.try_resolve_locale("fr_FR", ["fr_FR", "de_DE"]))

    def test_resolve_dash(self):
        self.assertEqual(
            "fr_FR",
            Languages.try_resolve_locale("fr-FR", ["fr_FR", "de_DE"]))

    def test_resolve_two_letter_fallback(self):
        self.assertEqual(
            "fr_FR",
            Languages.try_resolve_locale("fr", ["fr_FR", "de_DE"]))

    def test_resolve_english_short_circuit(self):
        self.assertIsNone(
            Languages.try_resolve_locale(
                "en-GB,fr;q=0.5", ["fr_FR", "de_DE"]))

    def test_resolve_preferred_before_lower_priority(self):
        self.assertEqual(
            "es_ES",
            Languages.try_resolve_locale(
                "es,de-DE;q=0.8,fr;q=0.5", ["es_ES", "de_DE", "fr_FR"]))

    def test_resolve_unknown_returns_none(self):
        self.assertIsNone(
            Languages.try_resolve_locale("zz-ZZ", ["fr_FR", "de_DE"]))


class TranslationEngineBaseTests(unittest.TestCase):

    def _build(self, evidence):
        source = MockSourceElement("source", {
            "Names": AspectPropertyValue(value=["Germany", "United Kingdom"])
        })
        engine = TranslationEngineBase(
            "source",
            [("Names", "NamesTranslated")],
            FR_SOURCE)
        pipeline = PipelineBuilder().add(source).add(engine).build()
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
        return flowdata.get("translation")

    def test_translates_from_evidence(self):
        result = self._build({"header.accept-language": "fr_FR"})
        translated = result.get("NamesTranslated")
        self.assertTrue(translated.has_value())
        self.assertEqual(
            ["Allemagne", "Royaume-Uni"], translated.value())

    def test_english_passthrough(self):
        result = self._build({"header.accept-language": "en-US,en;q=0.9"})
        translated = result.get("NamesTranslated")
        self.assertEqual(["Germany", "United Kingdom"], translated.value())

    def test_locale_from_filename(self):
        self.assertEqual(
            "fr_FR",
            TranslationEngineBase._get_language_name("countries.fr_FR.yml"))


# Each text the missing translation behavior accepts, and the member it
# names. The specification's names, the members' names and values, and
# other mixes of case and underscores are all accepted.
BEHAVIOR_TEXTS = {
    "Original": MissingTranslationBehavior.ORIGINAL,
    "original": MissingTranslationBehavior.ORIGINAL,
    "ORIGINAL": MissingTranslationBehavior.ORIGINAL,
    "EmptyString": MissingTranslationBehavior.EMPTY_STRING,
    "emptystring": MissingTranslationBehavior.EMPTY_STRING,
    "empty_string": MissingTranslationBehavior.EMPTY_STRING,
    "EMPTY_STRING": MissingTranslationBehavior.EMPTY_STRING,
    "Empty_String": MissingTranslationBehavior.EMPTY_STRING,
    "FlowError": MissingTranslationBehavior.FLOW_ERROR,
    "flowerror": MissingTranslationBehavior.FLOW_ERROR,
    "flow_error": MissingTranslationBehavior.FLOW_ERROR,
    "FLOW_ERROR": MissingTranslationBehavior.FLOW_ERROR,
}

# Values that name no member, each refused when the engine is built.
UNKNOWN_BEHAVIORS = (
    "", "Empty String", "Origin", "Missing", "flow-error", None, 1,
    ["Original"])

# The specification's name for each member.
SPECIFICATION_NAMES = {
    "Original": MissingTranslationBehavior.ORIGINAL,
    "EmptyString": MissingTranslationBehavior.EMPTY_STRING,
    "FlowError": MissingTranslationBehavior.FLOW_ERROR,
}

# The value a missing translation of "Spain" gives under each member, with
# the number of flow errors it adds.
MISSING_RESULTS = {
    MissingTranslationBehavior.ORIGINAL: (["Allemagne", "Spain"], 0),
    MissingTranslationBehavior.EMPTY_STRING: (["Allemagne", ""], 0),
    MissingTranslationBehavior.FLOW_ERROR: (["Allemagne", None], 1),
}


class MissingTranslationBehaviorTests(unittest.TestCase):

    """
    The missing translation behavior given as a member or as text, as a
    configuration file gives it, with anything else refused when the engine
    is built. The option takes the specification's name,
    missing_translation_behavior, and still takes the old name, behavior,
    with a DeprecationWarning.
    """

    def _engine(self, behavior):
        return TranslationEngineBase(
            "source",
            [("Names", "NamesTranslated")],
            FR_SOURCE,
            "fr_FR",
            behavior)

    def _missing(self, pipeline):
        """The translated names and the flow errors for a source holding a
        name with a translation and one without. The pipeline keeps errors
        on the flow data rather than raising them, so a flow error can be
        counted."""
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        self.addCleanup(flowdata.close)
        flowdata.process()
        translated = flowdata.get("translation").get("NamesTranslated")
        if isinstance(translated, AspectPropertyValue):
            translated = translated.value()
        return translated, len(flowdata.errors)

    def _pipeline(self, behavior):
        return self._pipeline_with(self._engine(behavior))

    @staticmethod
    def _pipeline_with(engine):
        source = MockSourceElement("source", {
            "Names": AspectPropertyValue(value=["Germany", "Spain"])
        })
        return PipelineBuilder({"suppress_process_exceptions": True}).add(
            source).add(engine).build()

    @staticmethod
    def _engine_with(**options):
        """An engine built with every option given by its name."""
        return TranslationEngineBase(
            source_element_data_key="source",
            translations=[("Names", "NamesTranslated")],
            sources=FR_SOURCE,
            fixed_language="fr_FR",
            **options)

    def test_from_value_names_each_member(self):
        for text, member in BEHAVIOR_TEXTS.items():
            with self.subTest(text):
                self.assertIs(
                    member, MissingTranslationBehavior.from_value(text))

    def test_from_value_returns_a_member_as_it_is(self):
        for member in MissingTranslationBehavior:
            with self.subTest(member.name):
                self.assertIs(
                    member, MissingTranslationBehavior.from_value(member))

    def test_each_text_takes_effect(self):
        for text, member in BEHAVIOR_TEXTS.items():
            with self.subTest(text):
                self.assertEqual(
                    MISSING_RESULTS[member],
                    self._missing(self._pipeline(text)))

    def test_each_member_takes_effect(self):
        for member, expected in MISSING_RESULTS.items():
            with self.subTest(member.name):
                self.assertEqual(
                    expected, self._missing(self._pipeline(member)))

    def test_unknown_value_is_refused_when_the_engine_is_built(self):
        for value in UNKNOWN_BEHAVIORS:
            with self.subTest(repr(value)):
                with self.assertRaises(ValueError) as raised:
                    self._engine(value)
                self.assertIn("EmptyString", str(raised.exception))

    def test_translator_takes_text(self):
        translator = Translator({"Germany": "Allemagne"}, "EmptyString")
        self.assertEqual("", translator.translate("Spain"))

    def test_specification_name_takes_effect_without_a_warning(self):
        for text, member in SPECIFICATION_NAMES.items():
            with self.subTest(text):
                with warnings.catch_warnings():
                    warnings.simplefilter("error", DeprecationWarning)
                    engine = self._engine_with(
                        missing_translation_behavior=text)
                self.assertEqual(
                    MISSING_RESULTS[member],
                    self._missing(self._pipeline_with(engine)))

    def test_old_name_still_takes_effect_with_a_warning(self):
        for text, member in SPECIFICATION_NAMES.items():
            with self.subTest(text):
                with self.assertWarns(DeprecationWarning) as warned:
                    engine = self._engine_with(behavior=text)
                self.assertIn(
                    "missing_translation_behavior", str(warned.warning))
                self.assertEqual(
                    MISSING_RESULTS[member],
                    self._missing(self._pipeline_with(engine)))

    def test_specification_name_wins_when_both_are_given(self):
        with self.assertWarns(DeprecationWarning):
            engine = self._engine_with(
                missing_translation_behavior="EmptyString",
                behavior="FlowError")
        self.assertEqual(
            MISSING_RESULTS[MissingTranslationBehavior.EMPTY_STRING],
            self._missing(self._pipeline_with(engine)))

    def test_neither_name_given_is_original(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            engine = self._engine_with()
        self.assertEqual(
            MISSING_RESULTS[MissingTranslationBehavior.ORIGINAL],
            self._missing(self._pipeline_with(engine)))

    def test_none_given_by_either_name_is_refused(self):
        with self.assertRaises(ValueError):
            self._engine_with(missing_translation_behavior=None)
        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(ValueError):
                self._engine_with(behavior=None)

    def test_translator_takes_both_names(self):
        translations = {"Germany": "Allemagne"}
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            translator = Translator(
                translations, missing_translation_behavior="EmptyString")
        self.assertEqual("", translator.translate("Spain"))
        with self.assertWarns(DeprecationWarning):
            translator = Translator(translations, behavior="EmptyString")
        self.assertEqual("", translator.translate("Spain"))
        with self.assertWarns(DeprecationWarning):
            translator = Translator(
                translations,
                missing_translation_behavior="Original",
                behavior="EmptyString")
        self.assertEqual("Spain", translator.translate("Spain"))

    def test_configuration_text_takes_effect(self):
        for text, member in (("EmptyString", "EMPTY_STRING"),
                             ("flow_error", "FLOW_ERROR"),
                             ("Original", "ORIGINAL")):
            with self.subTest(text):
                with warnings.catch_warnings():
                    warnings.simplefilter("error", DeprecationWarning)
                    pipeline = PipelineBuilder().build_from_configuration(
                        self._configuration(text))
                self.assertEqual(
                    MISSING_RESULTS[MissingTranslationBehavior[member]],
                    self._missing(pipeline))

    def test_configuration_with_an_unknown_value_is_refused(self):
        with self.assertRaises(ValueError):
            PipelineBuilder().build_from_configuration(
                self._configuration("EmptyStrings"))

    def test_configuration_with_the_old_name_still_takes_effect(self):
        with self.assertWarns(DeprecationWarning):
            pipeline = PipelineBuilder().build_from_configuration(
                self._configuration("EmptyString", "behavior"))
        self.assertEqual(
            MISSING_RESULTS[MissingTranslationBehavior.EMPTY_STRING],
            self._missing(pipeline))

    @staticmethod
    def _configuration(behavior, name="missing_translation_behavior"):
        """A pipeline configuration as a configuration file gives one, so
        every value in it is text, a list or a dictionary. Every option has
        the specification's name, unless the behavior's name is given."""
        return {
            "PipelineOptions": {
                "suppress_process_exceptions": True,
                "Elements": [
                    {
                        "elementPath": __name__,
                        "elementName": "MockSourceElement",
                        "elementParameters": {
                            "datakey": "source",
                            "contents": {"Names": ["Germany", "Spain"]},
                        },
                    },
                    {
                        "elementPath": (
                            "fiftyone_pipeline_translation."
                            "translation_engine_base"),
                        "elementName": "TranslationEngineBase",
                        "elementParameters": {
                            "source_element_data_key": "source",
                            "translations": [["Names", "NamesTranslated"]],
                            "sources": FR_SOURCE,
                            "fixed_language": "fr_FR",
                            name: behavior,
                        },
                    },
                ]
            }
        }


if __name__ == "__main__":
    unittest.main()

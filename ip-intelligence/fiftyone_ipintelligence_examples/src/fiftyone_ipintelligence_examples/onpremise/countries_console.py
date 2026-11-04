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

## @example onpremise/countries_console.py
# @brief Country Translation Console Example - On-premise
#
# This example shows how to turn the weighted country codes returned by the
# on-premise IP Intelligence engine into complete ordered lists of countries,
# most probable first, using the two country translation engines.
#
# You will learn:
# 1. How to add the country translation engines to a pipeline
# 2. How to supply the browser language so the names are localized
# 3. How to read the ordered "All" lists used to build a country dropdown
#
# This example uses a local IP intelligence data file (.ipi). A data file that
# contains country information is needed to see weighted countries lead the
# list; with the network-only ASN data file the lists are simply every known
# country in alphabetical order.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - fiftyone_ipintelligence_translation

import sys

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.onpremise.countries_pipeline import (
    add_country_translation)
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_VALUES
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME

# The browser language to translate the country names to. A value such as
# "fr_FR" or a full Accept-Language header is accepted; leave blank to keep the
# names in English.
TRANSLATION = "fr_FR"


class CountriesConsole():
    def run(self, data_file, logger, output):

        # Build a pipeline with the on-premise IP Intelligence engine, then add
        # the two country translation engines on top of it.
        builder = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = "LowMemory",
            usage_sharing = False,
            auto_update = False,
            licence_keys = "")
        add_country_translation(builder)
        pipeline = builder.add_logger(logger).build()

        # The pipeline is closed at the end of the with block, which
        # releases the native data it holds.
        with pipeline:
            ExampleUtils.check_data_file(pipeline, logger)

            for values in EVIDENCE_VALUES:
                self.analyseEvidence(values, pipeline, output)

    def analyseEvidence(self, evidence, pipeline, output):

        # The FlowData is closed at the end of the with block, which releases
        # the results of the lookup straight away.
        with pipeline.create_flowdata() as data:

            message = []
            message.append("Input values:\n")
            for key in evidence:
                message.append(f"\t{key}: {evidence[key]}\n")
            if TRANSLATION:
                message.append(f"\tquery.translation: {TRANSLATION}\n")
            output("".join(message))

            # Add the IP address evidence, and the language to translate to.
            data.evidence.add_from_dict(evidence)
            if TRANSLATION:
                data.evidence.add("query.translation", TRANSLATION)

            data.process()

            translated = data.get("countrynamestranslated")

            message = []
            message.append("Results:\n")
            self.outputList(
                translated, "CountryCodesGeographicalAll",
                "Geographical countries (most probable first)", message)
            self.outputList(
                translated, "CountryCodesPopulationAll",
                "Population countries (most probable first)", message)
            self.outputDropdown(translated, message)
            output("".join(message))

    def outputList(self, translated, property_name, label, message):
        value = translated.get(property_name)
        if value is not None and value.has_value():
            codes = value.value()
            message.append(f"\t{label}: {', '.join(codes)}\n")
        else:
            message.append(f"\t{label}: (no data)\n")

    def outputDropdown(self, translated, message):
        # The two lists are index-aligned, so option i is
        # (code[i], name[i]). Show the first few as a preview.
        codes = translated.get("CountryCodesGeographicalAll")
        names = translated.get("CountryNamesGeographicalAllTranslated")
        if (codes is None or names is None
                or not codes.has_value() or not names.has_value()):
            return
        codes = codes.value()
        names = names.value()
        message.append("\tDropdown (first 5 options):\n")
        for index in range(min(5, len(codes), len(names))):
            message.append(f"\t\t{codes[index]}: {names[index]}\n")


def main(argv):
    # Localized country names are UTF-8; reconfigure stdout so they are not
    # mangled on consoles with a non-UTF-8 default encoding (e.g. Windows
    # cp1252). Guarded because reconfigure is only available on Python 3.7+
    # text streams.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data_file = (
        argv[0] if len(argv) > 0
        else ExampleUtils.find_file(ASN_DATAFILE_NAME))

    logger = Logger(min_level="info")

    if data_file:
        CountriesConsole().run(data_file, logger, print)
    else:
        logger.log("error",
            "Failed to find an IP intelligence data file. Make sure the "
            "ip-intelligence-data submodule has been updated by running "
            "`git submodule update --recursive`, or supply the path to a "
            "data file as the first command line argument.")


if __name__ == "__main__":
    main(sys.argv[1:])

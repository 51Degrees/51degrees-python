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

## @example cloud/countries_console.py
# @brief Country Translation Console Example - Cloud
#
# This example shows how to list the countries an IP address is most likely
# in, with their names translated to the browser's language, using the
# 51Degrees cloud service.
#
# You will learn:
# 1. How to add the translated country names engine to a cloud pipeline
# 2. How to supply the browser language so the names are translated
# 3. How to read the "All" lists used to build a country dropdown
#
# A resource key carrying the IP intelligence and the translated country
# names properties is required. You can create one at
# https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=top
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_cloud.countries_translation_cloud import CountriesTranslationCloud
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.constants import Constants
from fiftyone_pipeline_core.logger import Logger

# The IP addresses to look up, each with the language a browser asks for,
# which the cloud service translates the country names into.
EVIDENCE_VALUES = [
    {
        Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "116.154.188.222",
        "header.accept-language": "fr-FR",
    },
    {
        Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "45.236.48.61",
        "header.accept-language": "de-DE",
    },
]

# How many entries of the "All" list to show for each address.
LIST_LENGTH = 10

# The line that introduces the "All" list of an address.
LIST_HEADING = "Every country, most likely first:"

# Where to create a resource key that carries the translated country names.
CONFIGURE = "https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=key-lacks-countries"

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("IP intelligence",
     "https://51degrees.com/ip-intelligence?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=find-out-more-ip-intelligence"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=find-out-more-resource-keys"),
    ("Pricing",
     "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=find-out-more-pricing"),
    ("IP intelligence for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/ip-intelligence"),
]


def print_find_out_more(output):
    message = ["=" * 79 + "\n", "Find out more:\n"]
    for label, url in FIND_OUT_MORE:
        message.append(f"\t{label}: {url}\n")
    output("".join(message))


class CountriesConsole():
    def run(self, resource_key, logger, output, cloud_endpoint = None):

        settings = { "resource_key": resource_key }
        if cloud_endpoint:
            settings["cloud_endpoint"] = cloud_endpoint

        # The IP intelligence pipeline builder adds the cloud request engine
        # and the IP intelligence cloud engine. The translated country names
        # engine reads its own section of the same response from the cloud
        # service, so it is added after them.
        pipeline = IpIntelligencePipelineBuilder(**settings) \
            .add(CountriesTranslationCloud()) \
            .add_logger(logger) \
            .build()

        # An engine whose properties the key does not carry has none.
        engine = pipeline.flow_elements_list[CountriesTranslationCloud.DATA_KEY]
        if engine.properties:
            for evidence in EVIDENCE_VALUES:
                self.analyse_evidence(evidence, pipeline, output)
        else:
            output(
                "The resource key in use does not carry the translated "
                f"country names. Create a key that does at {CONFIGURE}\n")

    def analyse_evidence(self, evidence, pipeline, output):

        data = pipeline.create_flowdata()

        message = ["Input values:\n"]
        for key, value in evidence.items():
            message.append(f"\t{key}: {value}\n")
        output("".join(message))

        data.evidence.add_from_dict(evidence)
        data.process()

        countries = data.get(CountriesTranslationCloud.DATA_KEY)

        message = ["Results:\n"]

        # The weighted list gives the countries the address is in, each with
        # its weighting from 0 to 1.
        names = ExampleUtils.get_value(
            countries, "countrynamesgeographicaltranslated")
        message.append("Countries the address is in, by weighting:\n")
        if self.has_value(names):
            for entry in names.value():
                weighting = entry.get("weighting", 0)
                message.append(f"\t{entry.get('value')}: {weighting:.0%}\n")
        else:
            message.append(f"\t{self.reason(names)}\n")

        # The "All" lists hold every country, the most likely first, and are
        # aligned by position, so the code and the name at one position
        # belong to the same country, as the options of a dropdown need.
        codes = ExampleUtils.get_value(
            countries, "countrycodesgeographicalall")
        all_names = ExampleUtils.get_value(
            countries, "countrynamesgeographicalalltranslated")
        if self.has_value(codes) and self.has_value(all_names):
            pairs = list(zip(codes.value(), all_names.value()))
            message.append(LIST_HEADING + "\n")
            for code, name in pairs[:LIST_LENGTH]:
                message.append(f"\t{code}: {name}\n")
            if len(pairs) > LIST_LENGTH:
                message.append(f"\tand {len(pairs) - LIST_LENGTH} more\n")
        else:
            missing = all_names if self.has_value(codes) else codes
            message.append(f"Every country: {self.reason(missing)}\n")

        culture = ExampleUtils.get_value(countries, "sortingcultureused")
        if self.has_value(culture):
            message.append(f"Names sorted for: {culture.value()}\n")

        output("".join(message))

    @staticmethod
    def has_value(value):
        return value is not None and value.has_value()

    @staticmethod
    def reason(value):
        if value is None:
            return "This property is not present in the result."
        return value.no_value_message()


def main(argv):
    # Use the supplied resource key or try to obtain one from the
    # environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key()

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if resource_key:
        CountriesConsole().run(
            resource_key,
            logger,
            print,
            ExampleUtils.get_cloud_endpoint())
    else:
        logger.log("error",
            "No resource key specified in the environment variable "
            f"'{ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR}'. The 51Degrees cloud "
            "service is accessed using a 'ResourceKey'. For more "
            "information see "
            "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=resource-key-required. "
            "A resource key with the properties required by this example "
            "can be created for free at "
            "https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-countries_console.py&utm_term=resource-key-required. "
            "Once complete, populate the environment variable mentioned at "
            "the start of this message with the key.")

    # Every end of the example, with or without a key, finishes here.
    print_find_out_more(print)

if __name__ == "__main__":
    main(sys.argv[1:])

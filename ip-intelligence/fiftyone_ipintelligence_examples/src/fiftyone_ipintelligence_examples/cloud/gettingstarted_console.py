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

## @example cloud/gettingstarted_console.py
# @brief Getting Started Console Example - Cloud
#
# This example shows how to use the 51Degrees cloud service to determine
# details about the network and location associated with an IP address.
#
# You will learn:
# 1. How to create a Pipeline that uses the 51Degrees cloud service
# 2. How to pass input data (evidence) to the Pipeline
# 3. How to retrieve the results
#
# A resource key is required. You can obtain one from
# https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=top
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.constants import Constants

# IP addresses to look up in this example. The IP address is supplied under
# the "query.client-ip" evidence key, which the cloud service treats as the
# IP address to look up (matching the .NET examples).
EVIDENCE_VALUES = [
    { Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "116.154.188.222" },
    { Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "1.3.32.31" },
    { Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "45.236.48.61" },
    { Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: "2001:0db8:085a:0000:0000:8a2e:0370:7334" },
]

# The properties displayed for each IP address. These mirror the .NET
# getting started example. Properties not present in the result are
# reported as such rather than causing an error.
OUTPUT_PROPERTIES = [
    "RegisteredName",
    "RegisteredOwner",
    "RegisteredCountry",
    "IpRangeStart",
    "IpRangeEnd",
    "Country",
    "CountryCode",
    "CountryCode3",
    "Region",
    "State",
    "Town",
    "Latitude",
    "Longitude",
    "Areas",
    "AccuracyRadiusMin",
    "TimeZoneOffset"]


class GettingStartedConsole():
    def run(self, resource_key, logger, output, cloud_endpoint = None):

        # In this example, we use the IpIntelligencePipelineBuilder and
        # configure it in code. For more information about pipelines in
        # general see the documentation at
        # https://51degrees.com/documentation/_pipeline_api__concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=run
        settings = {
            # Obtain a resource key from https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=run
            "resource_key": resource_key
        }
        if cloud_endpoint:
            settings["cloud_endpoint"] = cloud_endpoint

        pipeline = IpIntelligencePipelineBuilder(**settings) \
            .add_logger(logger) \
            .build()

        # carry out some sample lookups
        for values in EVIDENCE_VALUES:
            self.analyseEvidence(values, pipeline, output)

    def analyseEvidence(self, evidence, pipeline, output):

        # FlowData is a data structure that is used to convey information
        # required for the lookup and the results through the pipeline.
        data = pipeline.create_flowdata()

        message = []

        # List the evidence
        message.append("Input values:\n")
        for key in evidence:
            message.append(f"\t{key}: {evidence[key]}\n")

        output("".join(message))

        # Add the evidence values to the flow data
        data.evidence.add_from_dict(evidence)

        # Process the flow data.
        data.process()

        message = []
        message.append("Results:\n")

        # Now that it's been processed, the flow data will have been
        # populated with the result. In this case, we want information
        # about the IP address, which we can get by asking for a result
        # matching the key "ip".
        ip_data = data.ip

        # Display the results of the lookup. See the property dictionary
        # at https://51degrees.com/developers/property-dictionary?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=analyseevidence for
        # details of all available properties.
        for name in OUTPUT_PROPERTIES:
            self.outputValue(ip_data, name, message)
        output("".join(message))

    def outputValue(self, ip_data, name, message):
        # Individual result values have a wrapper called
        # `AspectPropertyValue`. This functions similarly to
        # a null-able type. If the value has not been set then trying to
        # access the `value` method will throw an exception.
        # `AspectPropertyValue` also includes the `no_value_message`
        # method, which describes why the value has not been set.
        # `get_value` returns None when the property is not present in the
        # result at all, rather than raising.
        value = ExampleUtils.get_value(ip_data, name.lower())
        if value is None:
            message.append(f"\t{name}: This property is not present in the result.\n")
        elif value.has_value():
            message.append(f"\t{name}: {ExampleUtils.format_value(value.value())}\n")
        else:
            message.append(f"\t{name}: {value.no_value_message()}\n")


def main(argv):
    # Use the supplied resource key or try to obtain one from the
    # environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key()

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if resource_key:
        GettingStartedConsole().run(
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
            "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=resource-key-required. "
            "A resource key with the properties required by this example "
            "can be created for free at https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_console.py&utm_term=resource-key-required. "
            "Once complete, populate the environment variable mentioned at "
            "the start of this message with the key.")

if __name__ == "__main__":
    main(sys.argv[1:])

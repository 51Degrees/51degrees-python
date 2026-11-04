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

## @example onpremise/gettingstarted_console.py
# @brief Getting Started Console Example - On-premise
#
# This example shows how to use 51Degrees On-premise IP intelligence to
# determine details about the network and location associated with an
# IP address.
#
# You will learn:
# 1. How to create a Pipeline that uses 51Degrees On-premise IP intelligence
# 2. How to pass input data (evidence) to the Pipeline
# 3. How to retrieve the results
#
# This example uses a local IP intelligence data file (.ipi). The
# ip-intelligence-data submodule provides a freely available data file;
# a more complete data file can be supplied as the first command line
# argument.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_VALUES
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME

# The properties displayed for each IP address. These mirror the .NET
# getting started example. Properties that are not present in the data file
# being used (for example the network-only ASN data file) are reported as
# such rather than causing an error.
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
    def run(self, data_file, logger, output):

        # In this example, we use the IpIntelligencePipelineBuilder
        # and configure it in code. For more information about
        # pipelines in general see the documentation at
        # https://51degrees.com/documentation/_pipeline_api__concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=run
        pipeline = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            # We use the low memory profile as its performance is
            # sufficient for this example. See the documentation for
            # more detail on this and other configuration options:
            # https://51degrees.com/documentation/_pipeline_api__features__automatic_datafile_updates.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=run
            # https://51degrees.com/documentation/_pipeline_api__features__usage_sharing.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=run
            performance_profile = "LowMemory",
            # inhibit sharing usage for this example, usually this
            # should be set "true"
            usage_sharing = False,
            # Inhibit auto-update of the data file for this example
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        ExampleUtils.check_data_file(pipeline, logger)

        # carry out some sample lookups
        for values in EVIDENCE_VALUES:
            self.analyseEvidence(values, pipeline, output)

    def analyseEvidence(self, evidence, pipeline, output):

        # FlowData is a data structure that is used to convey
        # information required for the lookup and the results
        # through the pipeline.
        # Information required is called "evidence", in this case an
        # IP address supplied under the "query.client-ip" key.
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

        # Now that it's been processed, the flow data will have
        # been populated with the result. In this case, we want
        # information about the IP address, which we can get by
        # asking for a result matching the key "ip"
        ip_data = data.ip

        # Display the results of the lookup. See the property
        # dictionary at https://51degrees.com/developers/property-dictionary?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=analyseevidence
        # for details of all available properties.
        for name in OUTPUT_PROPERTIES:
            self.outputValue(ip_data, name, message)
        output("".join(message))

    def outputValue(self, ip_data, name, message):
        # Individual result values have a wrapper called
        # `AspectPropertyValue`. This functions similarly to
        # a null-able type.
        # If the value has not been set then trying to access the
        # `value` method will throw an exception.
        # `AspectPropertyValue` also includes the `no_value_message`
        # method, which describes why the value has not been set.
        # `get_value` returns None when the property is not present in the
        # data file at all (for example the network-only ASN data file),
        # rather than raising.
        value = ExampleUtils.get_value(ip_data, name.lower())
        if value is None:
            message.append(f"\t{name}: This property is not present in the data file.\n")
        elif value.has_value():
            message.append(f"\t{name}: {ExampleUtils.format_value(value.value())}\n")
        else:
            message.append(f"\t{name}: {value.no_value_message()}\n")


def main(argv):
    # Use the supplied path for the data file or find the data file in the
    # project space.
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(ASN_DATAFILE_NAME)

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if data_file:
        GettingStartedConsole().run(data_file, logger, print)
    else:
        logger.log("error",
            "Failed to find an IP intelligence data file. Make sure the "
            "ip-intelligence-data submodule has been updated by running "
            "`git submodule update --recursive`, or supply the path to a "
            "data file as the first command line argument.")

if __name__ == "__main__":
    main(sys.argv[1:])

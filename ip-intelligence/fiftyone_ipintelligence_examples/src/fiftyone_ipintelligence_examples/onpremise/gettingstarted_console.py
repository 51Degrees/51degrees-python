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
# By default the example uses the free Lite IP intelligence data file, which
# it downloads when it is missing. The Lite data file has the registration
# properties, and the example shows each property only the Enterprise data
# file has as needing it. An Enterprise data file can be supplied as the first
# command line argument. Contact us for a copy:
# https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=header
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_VALUES
from fiftyone_ipintelligence_shared.example_constants import LITE_DATAFILE_NAME

# Where to ask for a copy of the Enterprise data file, tagged with this
# example.
CONTACT_US = "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_console.py&utm_term=enterprise-data-file"

# The properties displayed for each IP address. These mirror the .NET
# getting started example. A property the data file in use does not have is
# shown as needing the Enterprise data file.
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

        # The pipeline is closed at the end of the with block, which
        # releases the native data it holds. An application normally builds
        # one pipeline when it starts, uses it for every lookup, and closes
        # it when it stops.
        with pipeline:
            ExampleUtils.check_data_file(pipeline, logger)

            # carry out some sample lookups
            needs_enterprise = False
            for values in EVIDENCE_VALUES:
                needs_enterprise |= self.analyseEvidence(
                    values, pipeline, output)
            if needs_enterprise:
                output("\n" + ExampleUtils.get_enterprise_note(CONTACT_US))

    def analyseEvidence(self, evidence, pipeline, output):

        # FlowData is a data structure that is used to convey
        # information required for the lookup and the results
        # through the pipeline.
        # Information required is called "evidence", in this case an
        # IP address supplied under the "query.client-ip" key.
        # Closing the FlowData, which the with statement does at the end of
        # the block, releases the results of the lookup straight away,
        # rather than when the garbage collector next runs.
        with pipeline.create_flowdata() as data:

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
            # The engine says which properties its data file has.
            engine = pipeline.flow_elements_list["ip"]
            needs_enterprise = False
            for name in OUTPUT_PROPERTIES:
                needs_enterprise |= self.outputValue(
                    engine, ip_data, name, message)
            output("".join(message))
            return needs_enterprise

    def outputValue(self, engine, ip_data, name, message):
        # Individual result values have a wrapper called
        # `AspectPropertyValue`. This functions similarly to
        # a null-able type.
        # If the value has not been set then trying to access the
        # `value` method will throw an exception.
        # `AspectPropertyValue` also includes the `no_value_message`
        # method, which describes why the value has not been set.
        # A property the data file does not have needs the Enterprise data
        # file, and its value is not read.
        if not ExampleUtils.has_property(engine, name):
            message.append(f"\t{name}: {ExampleUtils.NEEDS_ENTERPRISE}\n")
            return True
        value = ip_data.get(name.lower())
        if value.has_value():
            message.append(f"\t{name}: {ExampleUtils.format_value(value.value())}\n")
        else:
            message.append(f"\t{name}: {value.no_value_message()}\n")
        return False


def main(argv):
    # Use the supplied path for the data file or find the data file in the
    # project space.
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(LITE_DATAFILE_NAME)

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if data_file:
        GettingStartedConsole().run(data_file, logger, print)
    else:
        logger.log("error",
            "Failed to find an IP intelligence data file. Make sure the "
            "data submodule is there, by running "
            "`git submodule update --init --recursive`, and run this "
            "example again to download the file, or supply the path to a "
            "data file as the first command line argument.")

if __name__ == "__main__":
    main(sys.argv[1:])

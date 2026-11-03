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

## @example cloud/getallproperties_console.py
# @brief Get All Properties Console Example - Cloud
#
# This example shows how to retrieve all of the IP intelligence properties
# available from the 51Degrees cloud service for a given IP address, and
# how to enumerate the values returned.
#
# A resource key is required. You can obtain one from
# https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-getallproperties_console.py&utm_term=top - make sure to include all of the
# properties that you want to see displayed by this example.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.constants import Constants

# The IP address that values will be retrieved for.
SOME_IP_ADDRESS = "8.8.8.8"

# Long values are truncated to this many characters for readability.
MAX_VALUE_LENGTH = 200


class GetAllPropertiesConsole():
    def run(self, resource_key, logger, output, cloud_endpoint = None):

        settings = {"resource_key": resource_key}
        if cloud_endpoint:
            settings["cloud_endpoint"] = cloud_endpoint

        pipeline = IpIntelligencePipelineBuilder(**settings) \
            .add_logger(logger) \
            .build()

        self.analyse_evidence(SOME_IP_ADDRESS, pipeline, output)

    def analyse_evidence(self, ip_address, pipeline, output):

        data = pipeline.create_flowdata()
        data.evidence.add_from_dict(
            {Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: ip_address})
        data.process()

        ip_data = data.ip

        output(f"What property values are associated with the IP "
               f"'{ip_address}'?")

        # Enumerate every property exposed by the engine and display its
        # value, sorted by property name.
        engine = pipeline.flow_elements_list["ip"]
        for property_name in sorted(engine.get_properties().keys()):
            output(f"\t{property_name} = "
                   f"{self.get_value_to_output(ip_data, property_name)}")

    def get_value_to_output(self, ip_data, property_name):
        # Retrieve the value via the engine. Missing properties return a
        # readable "Unknown" message rather than raising.
        value = ExampleUtils.get_human_readable(ip_data, property_name)
        if value is not None and len(value) > MAX_VALUE_LENGTH:
            value = value[:MAX_VALUE_LENGTH] + "..."
        return value


def main(argv):
    # Use the supplied resource key or try to obtain one from the
    # environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key()

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if resource_key:
        GetAllPropertiesConsole().run(
            resource_key, logger, print, ExampleUtils.get_cloud_endpoint())
    else:
        logger.log("error",
            "No resource key specified in the environment variable "
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees cloud "
            "service is accessed using a 'ResourceKey'. For more information "
            "see "
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-getallproperties_console.py&utm_term=resource-key-required. "
            "A resource key with the properties required by this example "
            "can be created for free at https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-getallproperties_console.py&utm_term=resource-key-required.")

if __name__ == "__main__":
    main(sys.argv[1:])

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

## @example cloud/metadata_console.py
# @brief Metadata Console Example - Cloud
#
# The cloud service exposes meta data that provides additional information
# about the various properties that might be returned. This example shows
# how to access that data and display the properties available, along with
# the evidence keys that are accepted by the service.
#
# Note that the property list reflects the properties used by the supplied
# resource key, rather than all properties the cloud service can return.
#
# A resource key is required. You can obtain one from
# https://configure.51degrees.com/
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter


class MetadataConsole():
    def run(self, resource_key, logger, output, cloud_endpoint = None):

        settings = {"resource_key": resource_key}
        if cloud_endpoint:
            settings["cloud_endpoint"] = cloud_endpoint

        pipeline = IpIntelligencePipelineBuilder(**settings) \
            .add_logger(logger) \
            .build()

        # The IP intelligence engine holds the property metadata.
        self.output_properties(pipeline.flow_elements_list["ip"], output)

        # We use the CloudRequestEngine to get the evidence key details
        # rather than the IP intelligence cloud engine. This is because the
        # IP intelligence cloud engine does not make use of any evidence
        # values directly; the CloudRequestEngine is the element that passes
        # the evidence to the cloud service.
        self.output_evidence_key_details(pipeline.flow_elements_list["cloud"], output)

    def output_properties(self, engine, output):
        output("IP Intelligence properties:")
        for property_name, property in engine.get_properties().items():
            output(f"\tProperty - {property_name} "
                   f"[Category: {property.get('category')}] ({property.get('type')})")

    def output_evidence_key_details(self, engine, output):
        evidence_key_filter = engine.get_evidence_key_filter()
        if isinstance(evidence_key_filter, BasicListEvidenceKeyFilter):
            # If the evidence key filter extends BasicListEvidenceKeyFilter
            # then we can display a list of accepted keys.
            output("Accepted evidence keys:")
            for key in evidence_key_filter.list:
                output(f"\t{key}")
        else:
            output(f"The evidence key filter has type "
                   f"{type(evidence_key_filter).__name__}. As this does not "
                   f"extend BasicListEvidenceKeyFilter, a list of accepted "
                   f"values cannot be displayed.")


def main(argv):
    # Use the supplied resource key or try to obtain one from the
    # environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key()

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if resource_key:
        MetadataConsole().run(
            resource_key, logger, print, ExampleUtils.get_cloud_endpoint())
    else:
        logger.log("error",
            "No resource key specified in the environment variable "
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees cloud "
            "service is accessed using a 'ResourceKey'. For more information "
            "see "
            "https://51degrees.com/documentation/_info__resource_keys.html. "
            "A resource key with the properties required by this example "
            "can be created for free at https://configure.51degrees.com.")

if __name__ == "__main__":
    main(sys.argv[1:])

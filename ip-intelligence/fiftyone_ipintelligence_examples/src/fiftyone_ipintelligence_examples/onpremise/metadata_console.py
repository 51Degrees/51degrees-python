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

## @example onpremise/metadata_console.py
# @brief Metadata Console Example - On-premise
#
# This example shows how to list the properties available from the
# on-premise IP intelligence engine, along with their types and
# descriptions.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import sys
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import ENTERPRISE_DATAFILE_NAME


class MetadataConsole():
    def run(self, data_file, logger, output):

        pipeline = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = "LowMemory",
            usage_sharing = False,
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        # The pipeline is closed at the end of the with block, which
        # releases the native data it holds.
        with pipeline:
            engine = pipeline.flow_elements_list["ip"]

            output("IP Intelligence properties:")
            for property_metadata in engine.properties.values():
                output(f"  {property_metadata['name']} ({property_metadata['type']}) - "
                       f"category: {property_metadata['category']}")
                if property_metadata.get("description"):
                    output(f"      {property_metadata['description']}")


def main(argv):
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(ENTERPRISE_DATAFILE_NAME)

    logger = Logger(min_level="info")

    if data_file:
        MetadataConsole().run(data_file, logger, print)
    else:
        logger.log("error",
            "Failed to find an IP intelligence data file. Supply its path "
            "as the first command line argument. To obtain an enterprise "
            "data file for testing, please contact us: "
            "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-metadata_console.py&utm_term=data-file-required")

if __name__ == "__main__":
    main(sys.argv[1:])

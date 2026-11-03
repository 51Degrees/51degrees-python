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

## @example onpremise/shareusage.py
#
# Demonstrates how to use the ShareUsage element directly to send evidence data
# to 51Degrees for usage sharing. This example shows how to:
#
# - Build a pipeline with only a ShareUsage element (no device detection)
# - Configure batch size (minimum entries per message)
# - Configure sampling rate (share percentage)
# - Process evidence from a YAML file
# - Add custom identifiers to track the data source
#
# This is useful for scenarios where you want to share usage data without
# performing device detection, or when you want fine-grained control over
# the share usage settings.
#
# **Note on Client IP Address:** The client IP address is included in the shared
# evidence solely for deduplication purposes. This allows 51Degrees' machine learning
# algorithms to properly weight evidence coming from different sources versus repeated
# evidence from the same source. Without this, the training data could be skewed by
# over-representing certain device configurations.
#
# **Identifying the Data Source (usage-from):** To help 51Degrees identify which
# customer or partner is sending usage data, you can add a custom "usage-from" header
# to the evidence. This is done by adding evidence with key `header.usage-from`
# and your company/application name as the value. In the XML packet sent to 51Degrees,
# this appears as: `<header Name="usage-from">YourCompanyName</header>`.
# Replace "YourCompanyName" in the `USAGE_FROM_VALUE` constant with your actual
# identifier before running this example.
#
# @include{doc} example-require-datafile.txt
#
# Required PyPi Dependencies:
# - [fiftyone_pipeline_engines_fiftyone](https://pypi.org/project/fiftyone-pipeline-engines-fiftyone/)
# - [ruamel.yaml](https://pypi.org/project/ruamel.yaml/)

import random
import sys
import time

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.example_constants import EVIDENCE_FILE_NAME
from ruamel.yaml import YAML

# Disable SSL verification for testing
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
_original_post = requests.post
requests.post = lambda *args, **kwargs: _original_post(*args, **{**kwargs, 'verify': False})

# Configurable settings
REQUESTED_PACKAGE_SIZE = 10    # Send after 10 entries (default is 10)
SHARE_PERCENTAGE = 1           # Share 100% of data (1 = 100%)
RECORDS_TO_PROCESS = 100       # Number of records to process

# Evidence key for client IP address - used for evidence deduplication (see note above)
EVIDENCE_CLIENTIP_KEY = "server.client-ip"

# Evidence key for identifying the source of share usage data.
# This adds a <header Name="usage-from">YourCompanyName</header> element to the XML packet,
# allowing 51Degrees to identify which customer/partner is sending the data.
# Replace "YourCompanyName" with your actual company or application identifier.
EVIDENCE_USAGE_FROM_KEY = "header.usage-from"
USAGE_FROM_VALUE = "YourCompanyName"


def generate_random_ip():
    """Generate a random IP address for demonstration purposes.
    In a real application, this would come from the HTTP request."""
    return f"{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def filter_evidence(evidence, prefix):
    """Filter evidence entries to only include those with the specified prefix."""
    return {k: v for k, v in evidence.items() if k.startswith(prefix)}


class ShareUsageExample():
    def run(self, evidence_yaml):
        """!
        Process a YAML representation of evidence and share it via the ShareUsage element.
        @param evidence_yaml: File containing the yaml representation of the evidence to process
        """

        print("Starting ShareUsage example")
        print(f"Settings: requested_package_size={REQUESTED_PACKAGE_SIZE}, "
            f"share_percentage={SHARE_PERCENTAGE * 100}%, "
            f"records_to_process={RECORDS_TO_PROCESS}")

        # Build the ShareUsage element with custom settings
        share_usage_element = ShareUsage(
            # Set the minimum number of entries before sending a batch
            requested_package_size=REQUESTED_PACKAGE_SIZE,
            # Share 100% of data (1 = 100%)
            share_percentage=SHARE_PERCENTAGE,
            # Disable repeat evidence filtering for this demo (share all evidence)
            interval=0,
            # Optional: set a custom URL (default is 51Degrees endpoint)
            # endpoint="https://your-custom-endpoint.com/usage",
            # Optional: block specific headers from being shared
            # header_blacklist=["authorization"],
            # Optional: include specific query string parameters
            # query_whitelist=["campaign"],
        )

        # Build a pipeline with only the ShareUsage element
        pipeline = PipelineBuilder().add(share_usage_element).build()

        print("Pipeline built successfully with ShareUsage element")

        # Load YAML evidence
        yaml = YAML()
        yaml_data = yaml.load_all(evidence_yaml)

        # Process evidence records
        count = 0
        for evidence in yaml_data:
            if count >= RECORDS_TO_PROCESS:
                break

            # Filter to only header.* entries
            data = filter_evidence(
                {k: str(v) for k, v in evidence.items()},
                "header.")

            # Add a client IP address to the evidence for deduplication purposes
            # (see class-level note). In a real web application, this would come
            # from the request (e.g., REMOTE_ADDR or X-Forwarded-For header)
            data[EVIDENCE_CLIENTIP_KEY] = generate_random_ip()

            # Add the usage-from identifier so 51Degrees knows the source of this data.
            # This appears as <header Name="usage-from">YourCompanyName</header> in the XML.
            data[EVIDENCE_USAGE_FROM_KEY] = USAGE_FROM_VALUE

            # Create flow data and process
            flow_data = pipeline.create_flowdata()
            flow_data.evidence.add_from_dict(data)
            flow_data.process()

            count += 1
            if count % 10 == 0:
                print(f"Processed {count} records")

        print(f"Finished processing {count} records")
        print("Waiting for share usage to complete sending...")

        # Give the background thread time to send any remaining data
        time.sleep(5)

        print("Done!")


def main(argv):
    # This file contains the 20,000 most commonly seen combinations of header values
    # that are relevant to device detection. For example, User-Agent and UA-CH headers.
    evidence_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(EVIDENCE_FILE_NAME)

    if evidence_file is not None:
        with open(evidence_file, "r") as input:
            ShareUsageExample().run(input)
    else:
        print("ERROR: Failed to find the evidence file. Make sure the "
            "device-detection-data submodule has been updated by running "
            "`git submodule update --recursive`.")


if __name__ == "__main__":
    main(sys.argv[1:])

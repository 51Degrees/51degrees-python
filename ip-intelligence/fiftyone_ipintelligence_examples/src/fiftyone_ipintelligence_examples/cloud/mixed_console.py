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

## @example cloud/mixed_console.py
# @brief Mixed Console Example - Cloud
#
# This example demonstrates using both Device Detection and IP Intelligence
# from the 51Degrees cloud service in a single pipeline. A single cloud
# request returns both device and IP intelligence data, which the two cloud
# engines then expose.
#
# A resource key configured with both device detection and IP intelligence
# properties is required. You can obtain one from
# https://51degrees.com/configure/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=top
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - fiftyone_devicedetection
#   (install with: pip install fiftyone_ipintelligence_examples[mixed])

import sys

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine

from fiftyone_ipintelligence_cloud.ipintelligence_cloud import IpIntelligenceCloud
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils

# Combined evidence: a User-Agent for device detection and an IP address for
# IP intelligence. These mirror the .NET mixed example.
COMBINED_EVIDENCE = [
    {
        "header.user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
        "query.client-ip": "62.61.32.31",
    },
    {
        "header.user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "query.client-ip": "45.236.48.61",
    },
    {
        "header.user-agent": "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "query.client-ip": "8.8.8.8",
    },
]

# Device detection properties to display.
DEVICE_PROPERTIES = [
    "IsMobile",
    "PlatformName",
    "PlatformVersion",
    "BrowserName",
    "BrowserVersion",
    "HardwareVendor",
    "DeviceType",
]

# IP intelligence properties to display.
IP_PROPERTIES = [
    "Country",
    "CountryCode",
    "RegisteredName",
    "RegisteredOwner",
    "RegisteredCountry",
    "Latitude",
    "Longitude",
]

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Device detection",
     "https://51degrees.com/device-detection?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=find-out-more-device-detection"),
    ("IP intelligence",
     "https://51degrees.com/ip-intelligence?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=find-out-more-ip-intelligence"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=find-out-more-resource-keys"),
    ("Pricing",
     "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=find-out-more-pricing"),
    ("IP intelligence for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/ip-intelligence"),
    ("Device detection for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/device-detection"),
]


class MixedConsole():
    def run(self, resource_key, logger, output, cloud_endpoint = None):

        # The device detection cloud engine is supplied by the device
        # detection package, an optional dependency of these examples.
        try:
            from fiftyone_devicedetection_cloud.devicedetection_cloud import DeviceDetectionCloud
        except ImportError:
            logger.log("error",
                "This example requires the 51Degrees device detection "
                "package. Install it with "
                "`pip install fiftyone_ipintelligence_examples[mixed]` or "
                "`pip install fiftyone_devicedetection`.")
            return

        settings = {"resource_key": resource_key}
        if cloud_endpoint:
            settings["cloud_endpoint"] = cloud_endpoint

        # A single CloudRequestEngine makes one request to the cloud service.
        # The device detection and IP intelligence cloud engines both read
        # from that single response.
        pipeline = PipelineBuilder() \
            .add(CloudRequestEngine(settings)) \
            .add(DeviceDetectionCloud()) \
            .add(IpIntelligenceCloud()) \
            .add_logger(logger) \
            .build()

        for evidence in COMBINED_EVIDENCE:
            self.analyse_evidence(evidence, pipeline, output)

    def analyse_evidence(self, evidence, pipeline, output):

        data = pipeline.create_flowdata()

        message = []
        message.append("=" * 70 + "\n")
        message.append("Input values:\n")
        for key in evidence:
            message.append(f"\t{key}: {evidence[key]}\n")
        output("".join(message))

        data.evidence.add_from_dict(evidence)
        data.process()

        message = []
        message.append("Device Detection Results:\n")
        for name in DEVICE_PROPERTIES:
            self.outputValue(data.device, name, message)

        message.append("\nIP Intelligence Results:\n")
        for name in IP_PROPERTIES:
            self.outputValue(data.ip, name, message)

        output("".join(message))

    def outputValue(self, aspect_data, name, message):
        # `get_value` returns None when the property is not present in the
        # result, rather than raising.
        value = ExampleUtils.get_value(aspect_data, name.lower())
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
        MixedConsole().run(
            resource_key, logger, print, ExampleUtils.get_cloud_endpoint())
    else:
        logger.log("error",
            "No resource key specified in the environment variable "
            f"'{ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR}'. The 51Degrees cloud "
            "service is accessed using a 'ResourceKey'. A resource key "
            "configured with both device detection and IP intelligence "
            "properties can be created at https://51degrees.com/configure/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-mixed_console.py&utm_term=resource-key-required.")

    # Printed after the results, when there is no resource key, and when
    # the device detection package is not installed.
    ExampleUtils.print_find_out_more(FIND_OUT_MORE)

if __name__ == "__main__":
    main(sys.argv[1:])

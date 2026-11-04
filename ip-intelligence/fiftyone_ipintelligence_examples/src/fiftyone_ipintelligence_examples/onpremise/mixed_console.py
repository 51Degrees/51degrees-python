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

## @example onpremise/mixed_console.py
# @brief Mixed Console Example - On-premise
#
# This example demonstrates using both Device Detection and IP Intelligence
# engines in a single on-premise pipeline. Each piece of evidence carries a
# User-Agent (used by device detection) and an IP address (used by IP
# intelligence), and both engines process the flow data.
#
# Two data files are required:
# - a Device Detection data file (.hash)
# - an IP Intelligence data file (.ipi)
#
# They may be supplied as the first two command line arguments.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - fiftyone_devicedetection
#   (install with: pip install fiftyone_ipintelligence_examples[mixed])

import sys

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.logger import Logger

from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import IpIntelligenceOnPremise
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME

# Default name of the device detection data file (the lite file the data
# repository links to).
HASH_DATAFILE_NAME = "51Degrees-LiteV4.1.hash"

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
        "header.user-agent": "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1",
        "query.client-ip": "2001:0db8:085a:0000:0000:8a2e:0370:7334",
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
    "ScreenPixelsWidth",
    "ScreenPixelsHeight",
]

# IP intelligence properties to display.
IP_PROPERTIES = [
    "Country",
    "CountryCode",
    "Region",
    "State",
    "Town",
    "Latitude",
    "Longitude",
    "RegisteredName",
    "RegisteredOwner",
    "RegisteredCountry",
    "IpRangeStart",
    "IpRangeEnd",
    "AccuracyRadiusMin",
    "TimeZoneOffset",
]


class MixedConsole():
    def run(self, device_file, ip_file, logger, output):

        # The device detection engine is supplied by the device detection
        # package, which is an optional dependency of these examples.
        try:
            from fiftyone_devicedetection_onpremise.devicedetection_onpremise import DeviceDetectionOnPremise
        except ImportError:
            logger.log("error",
                "This example requires the 51Degrees device detection "
                "package. Install it with "
                "`pip install fiftyone_ipintelligence_examples[mixed]` or "
                "`pip install fiftyone_devicedetection`.")
            return

        # Build the device detection and IP intelligence engines and add them
        # both to a single pipeline. Both engines process each flow data.
        device_engine = DeviceDetectionOnPremise(
            data_file_path = device_file,
            performance_profile = "LowMemory",
            auto_update = False,
            licence_keys = "")

        ip_engine = IpIntelligenceOnPremise(
            data_file_path = ip_file,
            performance_profile = "LowMemory",
            auto_update = False,
            licence_keys = "")

        pipeline = PipelineBuilder() \
            .add(device_engine) \
            .add(ip_engine) \
            .add_logger(logger) \
            .build()

        # The pipeline is closed at the end of the with block, which closes
        # both engines and releases the native data they hold.
        with pipeline:
            for evidence in COMBINED_EVIDENCE:
                self.analyse_evidence(evidence, pipeline, output)

    def analyse_evidence(self, evidence, pipeline, output):

        # The FlowData is closed at the end of the with block, which releases
        # the results of both engines straight away.
        with pipeline.create_flowdata() as data:

            message = []
            message.append("=" * 70 + "\n")
            message.append("Input values:\n")
            for key in evidence:
                message.append(f"\t{key}: {evidence[key]}\n")
            output("".join(message))

            # Add the evidence values to the flow data and process it. Both
            # engines run against the same flow data.
            data.evidence.add_from_dict(evidence)
            data.process()

            message = []

            # Device detection results, keyed under "device".
            message.append("Device Detection Results:\n")
            for name in DEVICE_PROPERTIES:
                self.outputValue(data.device, name, message)

            # IP intelligence results, keyed under "ip".
            message.append("\nIP Intelligence Results:\n")
            for name in IP_PROPERTIES:
                self.outputValue(data.ip, name, message)

            output("".join(message))

    def outputValue(self, aspect_data, name, message):
        # `get_value` returns None when the property is not present in the
        # data file, rather than raising.
        value = ExampleUtils.get_value(aspect_data, name.lower())
        if value is None:
            message.append(f"\t{name}: This property is not present in the data file.\n")
        elif value.has_value():
            message.append(f"\t{name}: {ExampleUtils.format_value(value.value())}\n")
        else:
            message.append(f"\t{name}: {value.no_value_message()}\n")


def main(argv):
    # Use the supplied paths for the data files, or find the device detection
    # and IP intelligence files in the project space.
    device_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(HASH_DATAFILE_NAME)
    ip_file = argv[1] if len(argv) > 1 else ExampleUtils.find_file(ASN_DATAFILE_NAME)

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if device_file and ip_file:
        MixedConsole().run(device_file, ip_file, logger, print)
    else:
        if not device_file:
            logger.log("error",
                "Failed to find a device detection data file. Supply its "
                "path as the first command line argument. Get the free Lite "
                "file by running "
                "cxx/data/get-data-files.sh 51Degrees-LiteV4.1.hash, or "
                "cxx/data/get-data-files.ps1 51Degrees-LiteV4.1.hash on "
                "Windows, which saves it in cxx/data/device-detection.")
        if not ip_file:
            logger.log("error",
                "Failed to find an IP intelligence data file. Make sure the "
                "data submodule is there, by running "
                "`git submodule update --init --recursive`, and run this "
                "example again to download the file, or supply the path as "
                "the second command line argument.")

if __name__ == "__main__":
    main(sys.argv[1:])

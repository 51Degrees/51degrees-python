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

import sys
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder
from fiftyone_devicedetection_examples.example_utils import ExampleUtils

# This example is displayed at the end of the [Configurator](https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-configurator_console.py&utm_term=top)
# process, which is used to create resource keys for use with the 51Degrees cloud service.
# 
# It shows how to call the cloud with the newly created key and how to access the values 
# of the selected properties.
#
# See [Getting Started](https://51degrees.com/documentation/_examples__device_detection__getting_started__console__cloud.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-configurator_console.py&utm_term=top)
# for a fuller example.
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection_cloud](https://pypi.org/project/fiftyone-devicedetection-cloud/)
class ConfiguratorConsole():
    def run(self, resource_key, logger, output):

        # Create a minimal pipeline to access the cloud engine
        # you only need one pipeline for multiple requests
        pipeline = DeviceDetectionCloudPipelineBuilder(
            resource_key = resource_key).add_logger(logger).build()

        # Get a flow data from the singleton pipeline for each detection
        data = pipeline.create_flowdata()
        
        # Add the evidence values to the flow data
        data.evidence.add(
            "header.user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36")
        data.evidence.add(
            "header.sec-ch-ua-mobile",
            "?0")
        data.evidence.add(
            "header.sec-ch-ua",
            "\" Not A; Brand\";v=\"99\", \"Chromium\";v=\"98\", "
            "\"Google Chrome\";v=\"98\"")
        data.evidence.add(
            "header.sec-ch-ua-platform",
            "\"Windows\"")
        data.evidence.add(
            "header.sec-ch-ua-platform-version",
            "\"14.0.0\"")

        # Process the flow data.
        data.process()

        # Get the results.
        device = data.device

        # Read through the helper so that a resource key without access to
        # 'ismobile' reports the reason the cloud service gave, rather than
        # stopping the example part way through.
        output("device.ismobile: " +
            f"{ExampleUtils.get_human_readable(device, 'ismobile')}")

def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key() 
    
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (resource_key):
        ConfiguratorConsole().run(resource_key, logger, print)

    else:
        logger.log("error",
            "No resource key specified in environment variable " +
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees " +
            "cloud service is accessed using a 'ResourceKey'. " +
            "For more detail see " +
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-configurator_console.py&utm_term=resource-key-required. " +
            "A resource key with the properties required by this " +
            "example can be created for free at " +
            "https://configure.51degrees.com/1QWJwHxl?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-configurator_console.py&utm_term=resource-key-required. " +
            "Once complete, populate the environment variable " +
            "mentioned at the start of this message with the key.")

if __name__ == "__main__":
    main(sys.argv[1:])

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
# This example shows how to use the 51Degrees Cloud service to determine details about a
# device based on its User-Agent and User-Agent Client Hint HTTP header values.
#
# You will learn:
# 1. How to create a Pipeline that uses the 51Degrees cloud service
# 2. How to pass input data (evidence) to the Pipeline
# 3. How to retrieve the results
#
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/version/4.5/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/cloud/gettingstarted_console.py).
#
# @include{doc} example-require-resourcekey.txt
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection_cloud](https://pypi.org/project/fiftyone-devicedetection-cloud/)

import json5
from pathlib import Path
import sys
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_examples.example_utils import ExampleUtils

class GettingStartedConsole():
    def run(self, config, logger, output):

        # In this example, we use the PipelineBuilder and configure it from a file.
        # For more information about builders in general see the documentation at
        # https://51degrees.com/documentation/_concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-gettingstarted_console.py&utm_term=run

        # Create the pipeline using the service provider and the configured options.
        pipeline = PipelineBuilder().add_logger(logger).build_from_configuration(config)

        # carry out some sample detections
        for values in self.EvidenceValues:
            self.analyseEvidence(values, pipeline, output)

    def analyseEvidence(self, evidence, pipeline, output):

        # FlowData is a data structure that is used to convey
        # information required for detection and the results of the
        # detection through the pipeline.
        # Information required for detection is called "evidence"
        # and usually consists of a number of HTTP Header field
        # values, in this case represented by a dictionary of header
        # name/value entries.
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
        # information about the device, which we can get by
        # asking for a result matching named "device"
        device = data.device

        # Display the results of the detection, which are called
        # device properties. See the property dictionary at
        # https://51degrees.com/developers/property-dictionary?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-gettingstarted_console.py&utm_term=analyseevidence
        # for details of all available properties.
        self.outputValue("Mobile Device", device.ismobile, message)
        self.outputValue("Platform Name", device.platformname, message)
        self.outputValue("Platform Version", device.platformversion, message)
        self.outputValue("Browser Name", device.browsername, message)
        self.outputValue("Browser Version", device.browserversion, message)
        output("".join(message))

    def outputValue(self, name, value, message):
        # Individual result values have a wrapper called
        # `AspectPropertyValue`. This functions similarly to
        # a null-able type.
        # If the value has not been set then trying to access the
        # `value` method will throw an exception.
        # `AspectPropertyValue` also includes the `no_value_message`
        # method, which describes why the value has not been set.
        message.append(
            f"\t{name}: {value.value()}\n" if value.has_value()
            else f"\t{name}: {value.no_value_message()}\n")


    # This collection contains the various input values that will 
    # be passed to the device detection algorithm.
    EvidenceValues = [
        # A User-Agent from a mobile device.
        { "header.user-agent":
            "Mozilla/5.0 (Linux; Android 9; SAMSUNG SM-G960U) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "SamsungBrowser/10.1 Chrome/71.0.3578.99 Mobile Safari/537.36" },
        # A User-Agent from a desktop device.
        { "header.user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/78.0.3904.108 Safari/537.36" },
        # Evidence values from a windows 11 device using a browser
        # that supports User-Agent Client Hints.
        { "header.user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36",
            "header.sec-ch-ua-mobile": "?0",
        "header.sec-ch-ua":
            "\" Not A; Brand\";v=\"99\", \"Chromium\";v=\"98\", "
            "\"Google Chrome\";v=\"98\"",
            "header.sec-ch-ua-platform": "\"Windows\"",
            "header.sec-ch-ua-platform-version": "\"14.0.0\"" }
    ]

def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key() 
    
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")
    
    # Load the configuration file
    configFile = Path(__file__).resolve().parent.joinpath("gettingstarted_console.json").read_text()
    config = json5.loads(configFile)

    # Get the resource key setting from the config file. 
    resourceKeyFromConfig = ExampleUtils.get_resource_key_from_config(config)
    configHasKey = resourceKeyFromConfig and resourceKeyFromConfig.startswith("!!") == False

    # If no resource key is specified in the config file then override it with the key
    # from the environment variable / command line. 
    if configHasKey == False:
        ExampleUtils.set_resource_key_in_config(config, resource_key)

    # If we don't have a resource key then log an error.
    if not ExampleUtils.get_resource_key_from_config(config):
        logger.log("error",
            "No resource key specified in the configuration file " +
            "'gettingstarted_console.json' or the environment variable " +
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees cloud " +
            "service is accessed using a 'ResourceKey'. For more information " +
            "see " +
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-gettingstarted_console.py&utm_term=resource-key-required. " +
            "A resource key with the properties required by this example can be " +
            "created for free at https://configure.51degrees.com/1QWJwHxl?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-gettingstarted_console.py&utm_term=resource-key-required. " +
            "Once complete, populate the config file or environment variable " +
            "mentioned at the start of this message with the key.")
    else:
        GettingStartedConsole().run(config, logger, print)

if __name__ == "__main__":
    main(sys.argv[1:])

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

## @example cloud/taclookup_console.py
# @brief TAC Lookup Console Example - Cloud
#
# This example shows the details of devices associated with a given 'Type Allocation Code' or 'TAC'.
# More background information on TACs can be found through various online sources such as Wikipedia: 
# https://en.wikipedia.org/wiki/Type_Allocation_Code
#
# You will learn:
# 1. How to create a Pipeline that uses the 51Degrees cloud service for TAC lookup
# 2. How to pass a TAC as evidence to the Pipeline
# 3. How to retrieve device details associated with the TAC
#
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/version/4.5/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/cloud/taclookup_console.py).
#
# @include{doc} example-require-resourcekey.txt
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
# - [json5](https://pypi.org/project/json5/)

import json5
from pathlib import Path
import sys
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_shared.constants import Constants

class TacLookupConsole():
    def run(self, config, logger, output):

        output("This example shows the details of devices " +
            "associated with a given 'Type Allocation Code' or 'TAC'.")
        output("More background information on TACs can be " +
            "found through various online sources such as Wikipedia: " +
            "https://en.wikipedia.org/wiki/Type_Allocation_Code")
        output("----------------------------------------")

        # In this example, we use the PipelineBuilder and configure it from a file.
        # For a demonstration of how to do this in code instead, see the
        # NativeModelLookup example.
        # For more information about builders in general see the documentation at
        # https://51degrees.com/documentation/_concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-taclookup_console.py&utm_term=run

        # Create the pipeline using the service provider and the configured options.
        pipeline = PipelineBuilder().add_logger(logger).build_from_configuration(config)
        
        # Pass a TAC into the pipeline and list the matching devices.
        self.analyseTac(self._tac1, pipeline, output)
        # Repeat for an alternative TAC.
        self.analyseTac(self._tac2, pipeline, output)

    def analyseTac(self, tac, pipeline, output):
        # Create the FlowData instance.
        data = pipeline.create_flowdata()
        # Add the TAC as evidence.
        data.evidence.add(Constants.EVIDENCE_QUERY_TAC_KEY, tac)
        # Process the supplied evidence.
        data.process()
        # Get result data from the flow data.
        result = data.hardware
        output(f"Which devices are associated with the TAC '{tac}'?")
        # The 'hardware.profiles' object contains one or more devices.
        # This is the same interface used for standard device detection, so we have
        # access to all the same properties.
        profiles = ExampleUtils.get_profiles(result)

        if len(profiles) == 0:
            output(ExampleUtils.get_no_profiles_message())
            return

        for device in profiles:
            vendor = ExampleUtils.get_human_readable(device, "hardwarevendor")
            name = ExampleUtils.get_human_readable(device, "hardwarename")
            model = ExampleUtils.get_human_readable(device, "hardwaremodel")
            output(f"\t{vendor} {name} ({model})")

    # Example values to use when looking up device details from TACs.
    _tac1 = "35925406"
    _tac2 = "86386802"

def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key() 
    
    # Configure a logger to output to the console.
    logger = Logger()
    
    # Load the configuration file
    configFile = Path(__file__).resolve().parent.joinpath("taclookup_console.json").read_text()
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
            "No resource key specified on the command line or in " +
            f"the environment variable '{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. " +
            "The 51Degrees cloud service is accessed using a 'ResourceKey'. " +
            "For more information see " +
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-taclookup_console.py&utm_term=resource-key-required. " +
            "TAC lookup is not available as a free service. This means " +
            "that you will first need a license key, which can be purchased " +
            "from our pricing page: https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-taclookup_console.py&utm_term=resource-key-required. Once this is " +
            "done, a resource key with the properties required by this example " +
            "can be created at https://configure.51degrees.com/QKyYH5XT?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-taclookup_console.py&utm_term=resource-key-required. You " +
            "can now populate the environment variable mentioned at the start " +
            "of this message with the resource key or pass it as the first " +
            "argument on the command line.")
    else:
        TacLookupConsole().run(config, logger, print)

if __name__ == "__main__":
    main(sys.argv[1:])

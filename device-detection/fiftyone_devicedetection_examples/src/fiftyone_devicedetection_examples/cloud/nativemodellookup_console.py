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

## @example cloud/nativemodellookup_console.py
# 
# This example shows how to use the 51Degrees Cloud service to lookup the details of a device 
# based on a given 'native model name'. Native model name is a string of characters that are 
# returned from a query to the device's OS. 
# There are different mechanisms to get native model names for 
# [Android devices](https://developer.android.com/reference/android/os/Build#MODEL) and 
# [iOS devices](https://gist.github.com/soapyigu/c99e1f45553070726f14c1bb0a54053b#file-machinename-swift)
# 
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/cloud/nativemodellookup_console.py). 
# 
# @include{doc} example-require-resourcekey.txt
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
#

import sys
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine
from fiftyone_devicedetection_shared.constants import Constants
from fiftyone_devicedetection_cloud.hardwareprofile_cloud import HardwareProfileCloud

class NativeModelLookupConsole():
    def run(self, resource_key, logger, output, cloudEndPoint = ""):

        output("This example shows the details of devices " +
            "associated with a given 'native model name'.")
        output("The native model name can be retrieved by " +
            "code running on the device (For example, a mobile app).")
        output("For Android devices, see " +
            "https://developer.android.com/reference/android/os/Build#MODEL")
        output("For iOS devices, see " +
            "https://gist.github.com/soapyigu/c99e1f45553070726f14c1bb0a54053b#file-machinename-swift")
        output("----------------------------------------")

        # This example creates the pipeline and engines in code. For a demonstration
        # of how to do this using a configuration file instead, see the TacLookup example.
        # For more information about builders in general see the documentation at
        # https://51degrees.com/documentation/_concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-nativemodellookup_console.py&utm_term=run
        cloudRequestEngineSettings = { "resource_key": resource_key }

        # If a cloud endpoint has been provided then set the
        # cloud pipeline endpoint. 
        if cloudEndPoint:
            cloudRequestEngineSettings["cloud_endpoint"] = cloudEndPoint
        
        # Create the cloud request engine.
        cloudEngine = CloudRequestEngine(cloudRequestEngineSettings)
        # Create the hardware profile engine to process the response from the
        # request engine.
        propertyKeyedEngine = HardwareProfileCloud()
        # Create the pipeline using the engines.
        pipeline = PipelineBuilder().add_logger(logger).add(cloudEngine).add(propertyKeyedEngine).build()

        # Pass a native model into the pipeline and list the matching devices.
        self.analyseModel(self._nativeModel1, pipeline, output)
        # Repeat for an alternative native model name.
        self.analyseModel(self._nativeModel2, pipeline, output)

    def analyseModel(self, nativemodel, pipeline, output):
        # Create the FlowData instance.
        data = pipeline.create_flowdata()
        # Add the native model key as evidence.
        data.evidence.add(Constants.EVIDENCE_QUERY_NATIVE_MODEL_KEY, nativemodel)
        # Process the supplied evidence.
        data.process()
        # Get result data from the flow data.
        result = data.hardware
        output("Which devices are associated with the " +
            f"native model name '{nativemodel}'?")
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

    # Example values to use when looking up device details from native model names.
    _nativeModel1 = "SC-03L"
    _nativeModel2 = "iPhone11,8"

def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key() 
    
    # Configure a logger to output to the console.
    logger = Logger()

    if (resource_key):
        NativeModelLookupConsole().run(resource_key, logger, print)
    else:
        logger.log("error",
            "No resource key specified on the command line or in the " +
            f"environment variable '{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. " +
            "The 51Degrees cloud service is accessed using a 'ResourceKey'. " +
            "For more information " +
            "see https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-nativemodellookup_console.py&utm_term=resource-key-required. " +
            "Native model lookup is not available as a free service. This means that " +
            "you will first need a license key, which can be purchased from our " +
            "pricing page: https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-nativemodellookup_console.py&utm_term=resource-key-required. Once this is done, a resource " +
            "key with the properties required by this example can be created at " +
            "https://configure.51degrees.com/QKyYH5XT?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-nativemodellookup_console.py&utm_term=resource-key-required. You can now populate the " +
            "environment variable mentioned at the start of this message with the " +
            "resource key or pass it as the first argument on the command line.")

if __name__ == "__main__":
    main(sys.argv[1:])

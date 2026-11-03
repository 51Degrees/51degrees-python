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
#
# The cloud service exposes meta data that can provide additional information about the various 
# properties that might be returned.
# This example shows how to access this data and display the values available.
# 
# A list of the properties will be displayed, along with some additional information about each
# property. Note that this is the list of properties used by the supplied resource key, rather
# than all properties that can be returned by the cloud service.
# 
# In addition, the evidence keys that are accepted by the service are listed. These are the 
# keys that, when added to the evidence collection in flow data, could have some impact on the
# result that is returned.
# 
# Bear in mind that this is a list of ALL evidence keys accepted by all products offered by the 
# cloud. If you are only using a single product (for example - device detection) then not all
# of these keys will be relevant.
# 
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/cloud/metadata_console.py). 
# 
# @include{doc} example-require-resourcekey.txt
# 
# Required PyPi Dependencies:
# - [fiftyone_devicedetection_cloud](https://pypi.org/project/fiftyone-devicedetection-cloud/)
# 

from pathlib import Path
import sys
from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_devicedetection_examples.example_utils import ExampleUtils

bgRed = "\u001b[41m"
fgWhite = "\u001b[37;1m"
colReset = "\u001b[0m"

class MetaDataConsole():
    def run(self, resource_key, logger, output):

        pipeline = DeviceDetectionCloudPipelineBuilder(
            resource_key = resource_key).add_logger(logger).build()

        self.outputProperties(pipeline.get_element("device"), output)
        # We use the CloudRequestEngine to get evidence key details, rather than the
        # DeviceDetectionCloudEngine.
        # This is because the DeviceDetectionCloudEngine doesn't actually make use
        # of any evidence values. It simply processes the JSON that is returned
        # by the call to the cloud service that is made by the CloudRequestEngine.
        # The CloudRequestEngine is actually taking the evidence values and passing
        # them to the cloud, so that's the engine we want the keys from.
        self.outputEvidenceKeyDetails(pipeline.get_element("cloud"), output)


    def outputEvidenceKeyDetails(self, engine, output):
        if (issubclass(type(engine.get_evidence_key_filter()), BasicListEvidenceKeyFilter)):
            
            # If the evidence key filter extends BasicListEvidenceKeyFilter then we can
            # display a list of accepted keys.
            filter = engine.get_evidence_key_filter()
            output("Accepted evidence keys:")
            for key in filter.list:
                output(f"\t{key}")
        else:
            output("The evidence key filter has type " +
                f"{type(engine.get_evidence_key_filter())}. As this does not extend " +
                "BasicListEvidenceKeyFilter, a list of accepted values cannot be " +
                "displayed. As an alternative, you can pass evidence keys to " +
                "filter.filter_evidence_key(string) to see if a particular key will be included " +
                "or not.")
            output("For example, header.user-agent is " +
                ("" if engine.get_evidence_key_filter().filter_evidence_key("header.user-agent") else "not ") +
                "accepted.")


    def outputProperties(self, engine, output):
        for propertyName, property in engine.get_properties().items():
            # Output some details about the property.
            # If we're outputting to console then we also add some formatting to make it 
            # more readable.
            output(f"{bgRed}{fgWhite}Property - {propertyName}{colReset}" +
                f"[Category: {property['category']}] ({property['type']})")

def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key() 
    
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (resource_key):
        MetaDataConsole().run(resource_key, logger, print)

    else:
        logger.log("error",
            "No resource key specified in environment variable " +
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees " +
            "cloud service is accessed using a 'ResourceKey'. " +
            "For more detail see " +
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-metadata_console.py&utm_term=resource-key-required. " +
            "A resource key with the properties required by this " +
            "example can be created for free at " +
            "https://configure.51degrees.com/1QWJwHxl?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-metadata_console.py&utm_term=resource-key-required. " +
            "Once complete, populate the environment variable " +
            "mentioned at the start of this message with the key.")

if __name__ == "__main__":
    main(sys.argv[1:])
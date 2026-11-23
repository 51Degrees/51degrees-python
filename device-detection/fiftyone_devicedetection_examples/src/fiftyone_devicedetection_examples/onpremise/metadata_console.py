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
#
# The device detection data file contains meta data that can provide additional information
# about the various records in the data model.
# This example shows how to access this data and display the values available.
# 
# A list of the properties will be displayed, along with some additional information about each
# property.
# 
# Finally, the evidence keys that are accepted by device detection are listed. These are the 
# keys that, when added to the evidence collection in flow data, could have some impact on the
# result returned by device detection.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/onpremise/metadata_console.py). 
# 
# @include{doc} example-require-datafile.txt
# 
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
# 

from pathlib import Path
import sys
from fiftyone_devicedetection.devicedetection_pipelinebuilder import DeviceDetectionPipelineBuilder
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.example_constants import EVIDENCE_VALUES
from fiftyone_devicedetection_shared.example_constants import LITE_DATAFILE_NAME

# Where to ask for a copy of the Enterprise data file, tagged with this
# example.
CONTACT_US = "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=enterprise-data-file"

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Device detection",
     "https://51degrees.com/device-detection?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=find-out-more-device-detection"),
    ("Enterprise data file",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=find-out-more-enterprise-data-file"),
    ("Device detection for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/device-detection"),
    ("Device detection engine",
     "https://github.com/51Degrees/51degrees-cxx"),
]

bgRed = "\u001b[41m"
fgWhite = "\u001b[37;1m"
colReset = "\u001b[0m"

class MetaDataConsole():
    def run(self, data_file, logger, output):

        # In this example, we use the DeviceDetectionPipelineBuilder
        # and configure it in code. For more information about
        # pipelines in general see the documentation at
        # https://51degrees.com/documentation/_pipeline_api__concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=run
        pipeline = DeviceDetectionPipelineBuilder(
            data_file_path = data_file,
            # We use the low memory profile as its performance is
            # sufficient for this example. See the documentation for
            # more detail on this and other configuration options:
            # https://51degrees.com/documentation/_device_detection__features__performance_options.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=run
            # https://51degrees.com/documentation/_pipeline_api__features__automatic_datafile_updates.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=run
            # https://51degrees.com/documentation/_pipeline_api__features__usage_sharing.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=run
            performance_profile = "LowMemory",
            # inhibit sharing usage for this test, usually this
            # should be set "true"
            usage_sharing = False,
            # Inhibit auto-update of the data file for this example
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        # The pipeline is closed at the end of the with block, which
        # releases the native data it holds.
        with pipeline:
            self.outputProperties(pipeline.get_element("device"), output)
            self.outputEvidenceKeyDetails(pipeline.get_element("device"), output)

            ExampleUtils.check_data_file(pipeline, logger)
            if ExampleUtils.is_lite_data_file(pipeline.get_element("device")):
                output("")
                output(ExampleUtils.get_enterprise_offer(CONTACT_US))


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
    # In this example, by default, the 51degrees "Lite" file needs to be
    # somewhere in the project space, or you may specify another file as
    # a command line parameter.
    #
    # Note that the Lite data file is only used for illustration, and has
    # a small number of Properties.
    # Contact us for a copy of the Enterprise data file:
    # https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-metadata_console.py&utm_term=main
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(LITE_DATAFILE_NAME)
    
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (data_file != None):
        MetaDataConsole().run(data_file, logger, print)
    else:
        logger.log("error",
            "Failed to find a device detection data file. Make sure the " +
            "data submodule is there, by running " +
            "`git submodule update --init --recursive`, and run this " +
            "example again to download the file.")

    ExampleUtils.print_find_out_more(FIND_OUT_MORE)

if __name__ == "__main__":
    main(sys.argv[1:])
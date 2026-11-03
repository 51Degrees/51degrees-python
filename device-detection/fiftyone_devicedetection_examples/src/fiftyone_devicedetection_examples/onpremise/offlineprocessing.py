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

## @example onpremise/offlineprocessing.py
# 
# Provides an example of processing a YAML file containing evidence for device detection. 
# There are 20,000 examples in the supplied file of evidence representing HTTP Headers.
# For example:
# 
# ```
# header.user-agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
# header.sec-ch-ua: '" Not A;Brand";v="99", "Chromium";v="98", "Google Chrome";v="98"'
# header.sec-ch-ua-full-version: '"98.0.4758.87"'
# header.sec-ch-ua-mobile: '?0'
# header.sec-ch-ua-platform: '"Android"'
# ```
# 
# We create a device detection pipeline to read the data and find out about the associated device,
# we write this data to a YAML formatted output stream.
# 
# As well as explaining the basic operation of off line processing using the defaults, for
# advanced operation this example can be used to experiment with tuning device detection for
# performance and predictive power using Performance Profile, Graph and Difference and Drift 
# settings.
# 
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/onpremise/offlineprocessing.py). 
# 
# @include{doc} example-require-datafile.txt
# 
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
# - [ruamel.yaml](https://pypi.org/project/ruamel.yaml/)

from pathlib import Path
import sys
from fiftyone_devicedetection.devicedetection_pipelinebuilder import DeviceDetectionPipelineBuilder
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_shared.example_constants import LITE_DATAFILE_NAME
from fiftyone_devicedetection_shared.example_constants import EVIDENCE_FILE_NAME
from ruamel.yaml import YAML

class OfflineProcessing():
    def run(self, data_file, evidence_yaml, logger, output):
        """!
        Process a YAML representation of evidence - and create a YAML output containing 
        the processed evidence.
        @param data_file: The path to the device detection data file
        @param evidence_yaml: File containing the yaml representation of the evidence to process
        @param logger: Logger to use within the pipeline
        @param output: Output file to write results to
        """

        # In this example, we use the DeviceDetectionPipelineBuilder
        # and configure it in code. For more information about
        # pipelines in general see the documentation at
        # https://51degrees.com/documentation/_concepts__configuration__builders__index.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=run
        pipeline = DeviceDetectionPipelineBuilder(
            data_file_path = data_file,
            # We use the low memory profile as its performance is
            # sufficient for this example. See the documentation for
            # more detail on this and other configuration options:
            # https://51degrees.com/documentation/_device_detection__features__performance_options.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=run
            # https://51degrees.com/documentation/_features__automatic_datafile_updates.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=run
            # https://51degrees.com/documentation/_features__usage_sharing.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=run
            performance_profile = "LowMemory",
            # inhibit sharing usage for this test, usually this
            # should be set "true"
            # In general, off line processing usage should NOT be shared back to 51Degrees.
            # This is because it will not contain the full set of information that is 
            # required by our data processing back-end and will be discarded.
            # If you specifically want to share data that is being processed off line
            # in order to help us improve detection of new devices/browsers/etc, then
            # this additional data will need to be collected and included as evidence
            # to the Pipeline. See
            # https://51degrees.com/documentation/_features__usage_sharing.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=run#Low_Level_Usage_Sharing
            # for more details on this.
            usage_sharing = False,
            # Inhibit auto-update of the data file for this example
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        records = 0
        yaml = YAML()
        # Replace tab characters as they are not valid in unquoted YAML values
        # and some evidence files contain them in user-agent strings.
        content = evidence_yaml.read().replace('\t', ' ')
        yaml_data = yaml.load_all(content)
        
        try:
            # Keep going as long as we have more document records.
            for evidence in yaml_data:
                # Output progress.
                records = records + 1
                if (records % 100 == 0):
                    logger.log("info", f"Processed {records} records")

                # write the yaml document separator
                print("---", file = output)
                # Pass the record to the pipeline as evidence so that it can be analyzed
                headers = {}
                for key in evidence:
                    # Convert to string - YAML may parse values like ?1 as booleans
                    # Keys already have header. prefix in the YAML file
                    headers[key] = str(evidence[key])

                self.analyseEvidence(headers, pipeline, output, yaml)
        except BaseException as err:
            # We can't read the evidence values, so cant write them to the output. Will just
            # have to skip this entry.
            logger.log("error", err)

        # write the yaml document end marker
        print("...", file = output)

        ExampleUtils.check_data_file(pipeline, logger)

    def analyseEvidence(self, evidence, pipeline, output, yaml):
        # FlowData is a data structure that is used to convey information required for
        # detection and the results of the detection through the pipeline.
        # Information required for detection is called "evidence" and usually consists
        # of a number of HTTP Header field values, in this case represented by a
        # dictionary of header name/value entries.
        data = pipeline.create_flowdata()
        # Add the evidence values to the flow data
        data.evidence.add_from_dict(evidence)
        # Process the flow data.
        data.process()

        device = data.device

        values = {}
        # Add the evidence values to the output
        for key in evidence:
            values[key] = evidence[key]
        # Now add the values that we want to store against the record.
        values["device.ismobile"] = device.ismobile.value() if device.ismobile.has_value() else "Unknown"
        values["device.platformname"] = ExampleUtils.get_human_readable(device, "platformname")
        values["device.platformversion"] = ExampleUtils.get_human_readable(device, "platformversion")
        values["device.browsername"] = ExampleUtils.get_human_readable(device, "browsername")
        values["device.browserversion"] = ExampleUtils.get_human_readable(device, "browserversion")
        values["device.tac"] = ExampleUtils.get_human_readable(device, "tac")
        values["device.devicetype"] = ExampleUtils.get_human_readable(device, "devicetype")
        values["device.hardwarevendor"] = ExampleUtils.get_human_readable(device, "hardwarevendor")
        values["device.hardwarename"] = ExampleUtils.get_human_readable(device, "hardwarename")
        values["device.hardwaremodel"] = ExampleUtils.get_human_readable(device, "hardwaremodel")
        values["device.nativedevice"] = ExampleUtils.get_human_readable(device, "nativedevice")
        values["device.nativename"] = ExampleUtils.get_human_readable(device, "nativename")
        values["device.nativemodel"] = ExampleUtils.get_human_readable(device, "nativemodel")
        # DeviceId is a unique identifier for the combination of hardware, operating
        # system, browser and crawler that has been detected.
        # Our device detection solution uses machine learning to find the optimal
        # way to identify devices based on the real-world evidence values that we
        # observe each day.
        # As this changes over time, the result of detection can potentially change
        # as well. By storing the device id, we can use this as a lookup in future
        # rather than performing detection with the original evidence again.
        # Do this by passing an evidence entry with:
        # key = query.51D_ProfileIds
        # value = [the device id]
        # This is much faster and avoids the potential for getting a different 
        # result.
        values["device.deviceid"] = ExampleUtils.get_human_readable(device, "deviceid")
        yaml.dump(values, output)

def main(argv):
    # In this example, by default, the 51degrees "Lite" file needs to be
    # somewhere in the project space, or you may specify another file as
    # a command line parameter.
    #
    # Note that the Lite data file is only used for illustration, and has
    # limited accuracy and capabilities.
    # Find out about the Enterprise data file on our pricing page:
    # https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-offlineprocessing.py&utm_term=main
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(LITE_DATAFILE_NAME)
    # This file contains the 20,000 most commonly seen combinations of header values 
    # that are relevant to device detection. For example, User-Agent and UA-CH headers.
    evidence_file = argv[1] if len(argv) > 1 else ExampleUtils.find_file(EVIDENCE_FILE_NAME)
    # Finally, get the location for the output file. Use the same location as the
    # evidence if a path is not supplied on the command line.
    output_file = argv[2] if len(argv) > 2 else Path.joinpath(Path(evidence_file).absolute().parent, "offline-processing-output.yml")
   
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (data_file != None):
        with open(output_file, "w") as output:
            with open(evidence_file, "r") as input:
                OfflineProcessing().run(data_file, input, logger, output)
        logger.log("info",
            f"Processing complete. See results in: '{output_file}'")
    else:
        logger.log("error",
            "Failed to find a device detection data file. Make sure the " +
            "device-detection-data submodule has been updated by running " +
            "`git submodule update --recursive`.")

if __name__ == "__main__":
    main(sys.argv[1:])

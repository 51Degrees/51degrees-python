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
# Provides an example of processing a YAML file containing evidence for
# IP intelligence. There are 20,000 IP addresses in the supplied file of
# evidence records ('evidence.yml' in the ip-intelligence-data
# repository).
#
# We create a pipeline using the on-premise engine, deserialize the
# YAML evidence records, pass each entry to the pipeline and write the
# resolved properties out to another YAML file.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - ruamel.yaml

import sys
import io
from ruamel.yaml import YAML

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_FILE_NAME
from fiftyone_ipintelligence_shared.example_constants import ENTERPRISE_DATAFILE_NAME

# Number of evidence records to process in this example.
RECORD_LIMIT = 100


class OfflineProcessing():
    def run(self, data_file, evidence_yaml, logger, output):

        """!
        Process a YAML representation of evidence - and create a YAML
        output containing the processed evidence.
        """

        yaml = YAML()

        pipeline = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = "LowMemory",
            usage_sharing = False,
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        # The pipeline is closed at the end of the with block, which
        # releases the native data it holds.
        with pipeline:
            ExampleUtils.check_data_file(pipeline, logger)

            records = 0
            with open(evidence_yaml, "r") as fin:
                for evidence in yaml.load_all(fin):
                    if records >= RECORD_LIMIT:
                        break

                    # write the yaml document separator
                    output("---")
                    self.analyse_evidence(evidence, pipeline, output, yaml)
                    records += 1

            # write the yaml document end marker
            output("...")
            logger.log("info", f"Processed {records} evidence records")

    def analyse_evidence(self, evidence, pipeline, output, yaml):

        # The FlowData is closed at the end of the with block, once the
        # values needed have been read, which releases the results of the
        # lookup straight away.
        with pipeline.create_flowdata() as data:

            # Add the evidence values to the flow data. The YAML loader
            # returns a dict subclass so convert to a plain dict first.
            data.evidence.add_from_dict(dict(evidence))

            # Process the flow data.
            data.process()

            ip_data = data.ip

            result = dict(evidence)

            # Add the values that we want to store against the record.
            result["ip.registeredname"] = ExampleUtils.get_human_readable(ip_data, "registeredname")
            result["ip.registeredcountry"] = ExampleUtils.get_human_readable(ip_data, "registeredcountry")

        buffer = io.BytesIO()
        yaml.dump(result, buffer)
        output(buffer.getvalue().decode("utf-8").rstrip())


def main(argv):
    # Use the supplied path for the data file or find the enterprise file
    # in the project space.
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(ENTERPRISE_DATAFILE_NAME)
    evidence_file = argv[1] if len(argv) > 1 else ExampleUtils.find_file(EVIDENCE_FILE_NAME)

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if data_file and evidence_file:
        OfflineProcessing().run(data_file, evidence_file, logger, print)
    else:
        logger.log("error",
            "Failed to find a data file or evidence file. Make sure the "
            "ip-intelligence-data submodule has been updated by running "
            "`git submodule update --recursive`.")

if __name__ == "__main__":
    main(sys.argv[1:])

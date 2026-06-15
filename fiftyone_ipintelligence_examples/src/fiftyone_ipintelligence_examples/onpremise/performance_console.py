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

## @example onpremise/performance_console.py
# @brief Performance Console Example - On-premise
#
# This example measures the performance of the on-premise IP intelligence
# engine. It processes the IP addresses from the evidence file supplied in
# the ip-intelligence-data repository and reports the number of IP lookups
# performed per second.
#
# Requesting fewer properties reduces processing time. If you do not specify
# any properties then all properties are returned. See the documentation for
# more detail on performance options:
# https://51degrees.com/documentation/_features__performance_options.html
#
# A large enterprise data file is used with the low memory performance
# profile so that the (memory mapped) data file is shared rather than loaded
# into memory for every worker. To obtain an enterprise data file for
# testing, please contact us: https://51degrees.com/contact-us
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - ruamel.yaml

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

from ruamel.yaml import YAML

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import ENTERPRISE_DATAFILE_NAME
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_FILE_NAME

# The IP intelligence properties used to measure performance. Restricting the
# work to a single component keeps the benchmark focused on lookup speed.
PERFORMANCE_PROPERTY = "registeredcountry"


class PerformanceConsole():
    def run(self, data_file, evidence, logger, output, threads=None,
            performance_profile="MaxPerformance"):

        """!
        Build an on-premise pipeline and time how long it takes to process
        the supplied list of evidence records.
        """

        if threads is None:
            threads = cpu_count()

        # A benchmark normally uses the max performance profile, which loads
        # the whole data file into memory for the fastest lookups. The
        # enterprise IP intelligence data file is large (several GB), so a
        # single shared in-memory copy is used and the worker threads share
        # it. If memory is constrained, pass performance_profile="LowMemory"
        # to use the (slower) memory mapped profile instead.
        pipeline = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = performance_profile,
            usage_sharing = False,
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        ExampleUtils.check_data_file(pipeline, logger)

        def process(record):
            data = pipeline.create_flowdata()
            data.evidence.add_from_dict(record)
            data.process()
            value = ExampleUtils.get_value(data.ip, PERFORMANCE_PROPERTY)
            return value is not None and value.has_value()

        # Warm up so that any lazy initialisation is not included in the
        # timed run.
        for record in evidence[:min(len(evidence), 100)]:
            process(record)

        count = len(evidence)
        start = time.time()
        if threads > 1:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                list(executor.map(process, evidence))
        else:
            for record in evidence:
                process(record)
        elapsed = time.time() - start

        per_second = count / elapsed if elapsed > 0 else 0
        ms_per_lookup = (elapsed / count) * 1000 if count > 0 else 0

        output(f"Processed {count} IP addresses using {threads} thread(s)")
        output(f"Total time: {elapsed:.3f} seconds")
        output(f"IP lookups per second: {per_second:.0f}")
        output(f"Time per IP lookup (ms): {ms_per_lookup:.4f}")

        return {
            "DetectionsPerSecond": per_second,
            "MsPerDetection": ms_per_lookup,
        }


def load_evidence(evidence_file, record_limit):
    """!
    Read up to record_limit evidence records from the supplied YAML file.
    The loader returns a dict subclass, so each record is converted to a
    plain dict before use.
    """
    yaml = YAML(typ="safe")
    records = []
    with open(evidence_file, "r") as fin:
        for evidence in yaml.load_all(fin):
            if evidence is None:
                continue
            records.append(dict(evidence))
            if len(records) >= record_limit:
                break
    return records


def main(argv):
    ap = argparse.ArgumentParser(description="Run an IP intelligence benchmark.")
    ap.add_argument("-d", "--data_file", default=None,
        help="Path to the IP intelligence data file")
    ap.add_argument("-e", "--evidence_file", default=None,
        help="Path to the YAML evidence file")
    ap.add_argument("-j", "--json_output", default=None,
        help="Optional path to write JSON format results to")
    ap.add_argument("-n", "--record_limit", type=int, default=5000,
        help="Maximum number of evidence records to process")
    ap.add_argument("-t", "--threads", type=int, default=None,
        help="Number of worker threads (defaults to the number of CPUs)")
    ap.add_argument("-p", "--performance_profile", default="MaxPerformance",
        help="Performance profile: MaxPerformance (default) or LowMemory")
    args = ap.parse_args(argv)

    data_file = args.data_file or ExampleUtils.find_file(ENTERPRISE_DATAFILE_NAME)
    evidence_file = args.evidence_file or ExampleUtils.find_file(EVIDENCE_FILE_NAME)

    logger = Logger(min_level="info")

    if data_file and evidence_file:
        evidence = load_evidence(evidence_file, args.record_limit)
        results = PerformanceConsole().run(
            data_file, evidence, logger, print,
            threads=args.threads, performance_profile=args.performance_profile)
        if args.json_output:
            with open(args.json_output, "w") as fout:
                json.dump(results, fout)
    else:
        logger.log("error",
            "Failed to find a data file or evidence file. Make sure the "
            "ip-intelligence-data submodule has been updated by running "
            "`git submodule update --recursive`. To obtain an enterprise "
            "data file for testing, please contact us: "
            "https://51degrees.com/contact-us")

if __name__ == "__main__":
    main(sys.argv[1:])

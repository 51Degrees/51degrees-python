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
# https://51degrees.com/documentation/_features__performance_options.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-performance_console.py&utm_term=header
#
# The native engine holds the Python GIL for the duration of each lookup, so
# threads cannot run lookups in parallel. Parallelism therefore uses worker
# processes, each building its own pipeline. With the LowMemory profile the
# memory mapped data file is shared between the processes by the operating
# system, so a large enterprise data file is not duplicated per worker.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence
# - ruamel.yaml

import argparse
import json
import multiprocessing
import sys
import time
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

# The number of records processed before timing starts, so that any lazy
# initialisation is not included in the timed run.
WARM_UP_RECORDS = 100


def _build_pipeline(data_file, performance_profile, logger=None):
    builder = IpIntelligencePipelineBuilder(
        data_file_path = data_file,
        performance_profile = performance_profile,
        usage_sharing = False,
        auto_update = False,
        # Auto update is disabled, so the data file can be used in place.
        # This avoids every worker process spilling its own temporary copy
        # of a potentially very large file.
        create_temp_data_copy = False,
        licence_keys = "")
    if logger is not None:
        builder.add_logger(logger)
    return builder.build()


def _process_record(pipeline, record):
    data = pipeline.create_flowdata()
    data.evidence.add_from_dict(record)
    data.process()
    value = ExampleUtils.get_value(data.ip, PERFORMANCE_PROPERTY)
    return value is not None and value.has_value()


def _time_lookups(pipeline, records):

    """!
    Warm up, then time how long the pipeline takes to process the records.
    Returns the elapsed seconds.
    """

    for record in records[:min(len(records), WARM_UP_RECORDS)]:
        _process_record(pipeline, record)

    start = time.time()
    for record in records:
        _process_record(pipeline, record)
    return time.time() - start


def _worker(data_file, performance_profile, records, queue):

    """!
    Worker process entry point. Builds its own pipeline (the engine cannot be
    shared across processes), times its share of the records and reports the
    count and elapsed seconds back to the parent.
    """

    pipeline = _build_pipeline(data_file, performance_profile)
    elapsed = _time_lookups(pipeline, records)
    queue.put((len(records), elapsed))


class PerformanceConsole():
    def run(self, data_file, evidence, logger, output, workers=None,
            performance_profile="MaxPerformance"):

        """!
        Time how long it takes to process the supplied list of evidence
        records. With one worker the pipeline runs in this process; with
        more, the records are split across worker processes that each build
        their own pipeline, since the native lookup holds the GIL and
        threads cannot run lookups in parallel.
        """

        if workers is None:
            workers = cpu_count()

        count = len(evidence)

        if workers > 1:
            # Round-robin split so every worker gets a near equal share.
            chunks = [evidence[index::workers] for index in range(workers)]
            queue = multiprocessing.Queue()
            processes = [
                multiprocessing.Process(
                    target=_worker,
                    args=(data_file, performance_profile, chunk, queue))
                for chunk in chunks if chunk]
            for process in processes:
                process.start()
            results = [queue.get() for _process in processes]
            for process in processes:
                process.join()
            count = sum(records for records, _elapsed in results)
            # The workers run concurrently, so the slowest one defines the
            # wall time of the run.
            elapsed = max(elapsed for _records, elapsed in results)
        else:
            pipeline = _build_pipeline(data_file, performance_profile, logger)
            ExampleUtils.check_data_file(pipeline, logger)
            elapsed = _time_lookups(pipeline, evidence)

        per_second = count / elapsed if elapsed > 0 else 0
        ms_per_lookup = (elapsed / count) * 1000 if count > 0 else 0

        output(f"Processed {count} IP addresses using {workers} worker "
               f"process(es)")
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
    ap.add_argument("-w", "--workers", type=int, default=None,
        help="Number of worker processes (defaults to the number of CPUs)")
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
            workers=args.workers, performance_profile=args.performance_profile)
        if args.json_output:
            with open(args.json_output, "w") as fout:
                json.dump(results, fout)
    else:
        logger.log("error",
            "Failed to find a data file or evidence file. Make sure the "
            "ip-intelligence-data submodule has been updated by running "
            "`git submodule update --recursive`. To obtain an enterprise "
            "data file for testing, please contact us: "
            "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-performance_console.py&utm_term=main")

if __name__ == "__main__":
    main(sys.argv[1:])

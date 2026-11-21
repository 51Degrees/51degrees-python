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

"""!
Runs the web performance benchmark the performance step runs, as that step
runs it, with python and the --output option, on a free data file and a short
file of evidence so that it takes seconds. The step gives it the free Lite
file. This test gives it the free Asn file, which the other example tests use
and which is far smaller, because the benchmark measures any data file the
same way.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

from ruamel.yaml import YAML

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.example_constants import \
    ASN_DATAFILE_NAME, EVIDENCE_FILE_NAME

# The benchmark, in the same place as Device Detection's.
BENCHMARK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "performance-tests", "test_performance.py")

# The evidence records given to the benchmark, enough to time lookups
# without making the test slow.
RECORDS = 50

# Stops a run that never finishes. A run takes seconds, so this does not
# limit how fast the benchmark has to be.
HANG_TIMEOUT_SECONDS = 300


class WebPerformanceBenchmarkTests(unittest.TestCase):

    def setUp(self):
        self.data_file = ExampleUtils.find_file(ASN_DATAFILE_NAME)
        self.evidence_file = ExampleUtils.find_file(EVIDENCE_FILE_NAME)
        self.assertIsNotNone(
            self.data_file, f"{ASN_DATAFILE_NAME} was not found")
        self.assertIsNotNone(
            self.evidence_file, f"{EVIDENCE_FILE_NAME} was not found")
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def short_evidence(self, count):
        """The path of a file holding the first count records of the free
        evidence file, each as a document of its own."""
        yaml = YAML(typ="safe")
        with open(self.evidence_file, "r") as source:
            records = [dict(record) for record in itertools.islice(
                (record for record in yaml.load_all(source) if record),
                count)]
        self.assertEqual(count, len(records))
        evidence = os.path.join(self.folder, "evidence.yml")
        with open(evidence, "w") as target:
            yaml.dump_all(records, target)
        return evidence

    def test_times_every_record_and_writes_json(self):
        evidence = self.short_evidence(RECORDS)

        finished = subprocess.run(
            [sys.executable, BENCHMARK, self.data_file, evidence, "--output"],
            capture_output=True, text=True, timeout=HANG_TIMEOUT_SECONDS)

        self.assertEqual(0, finished.returncode,
                         finished.stdout + finished.stderr)
        results = json.loads(finished.stdout)
        self.assertEqual(RECORDS, results["Detections"])
        self.assertGreater(results["DetectionsPerSecond"], 0)
        self.assertGreater(results["RuntimeSeconds"], 0)
        self.assertGreater(results["AvgMillisecsPerDetection"], 0)

    def test_prints_nothing_without_the_output_option(self):
        evidence = self.short_evidence(RECORDS)

        finished = subprocess.run(
            [sys.executable, BENCHMARK, self.data_file, evidence],
            capture_output=True, text=True, timeout=HANG_TIMEOUT_SECONDS)

        self.assertEqual(0, finished.returncode,
                         finished.stdout + finished.stderr)
        self.assertEqual("", finished.stdout)
        self.assertIn(f"Benchmarking with {RECORDS} IP addresses",
                      finished.stderr)


if __name__ == "__main__":
    unittest.main()

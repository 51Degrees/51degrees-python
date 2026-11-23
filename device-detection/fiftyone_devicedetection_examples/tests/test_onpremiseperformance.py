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
Runs the on-premise performance example as a person runs it, with python -m,
once with no arguments and otherwise with its -d, -e and -j options, on the
free Lite data file and a short file of evidence records so that it takes
seconds. Its work is done under if __name__ == "__main__", in a separate
process for each processor, so it runs in a process of its own here.
"""

import ast
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import unittest

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise import performance
from fiftyone_devicedetection_shared.example_constants import \
    EVIDENCE_FILE_NAME, LITE_DATAFILE_NAME

MODULE = "fiftyone_devicedetection_examples.onpremise.performance"

# The User-Agents each process is given when the example runs normally,
# enough to time detection without making the test slow.
USER_AGENTS_PER_PROCESS = 10

# Stops a run that never finishes. A run takes seconds, so this does not
# limit how fast the example has to be.
HANG_TIMEOUT_SECONDS = 300

# The settings a fresh clone does not have, left out of the run with no
# arguments.
SETTINGS = ("_51DEGREES_DD_PATH", "_51DEGREES_LICENSE_KEY")

# The example prints its counts on a line starting with this, followed by a
# dictionary of them.
RESULTS_PREFIX = "Results "


def counts(output):
    """The counts of mobile, other and unknown User-Agents the example
    printed, or None when it printed none."""
    for line in output.splitlines():
        if line.startswith(RESULTS_PREFIX):
            return ast.literal_eval(line[len(RESULTS_PREFIX):])
    return None


class OnPremisePerformanceTests(unittest.TestCase):

    def setUp(self):
        self.data_file = ExampleUtils.find_file(LITE_DATAFILE_NAME)
        self.evidence_file = ExampleUtils.find_file(EVIDENCE_FILE_NAME)
        self.assertIsNotNone(
            self.data_file, f"{LITE_DATAFILE_NAME} was not found")
        self.assertIsNotNone(
            self.evidence_file, f"{EVIDENCE_FILE_NAME} was not found")
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        # The example starts one process for each processor.
        self.processes = multiprocessing.cpu_count()

    def run_example(self, count):
        """Runs the example on the first count User-Agents of the free
        evidence file, each written as a record of its own, and returns
        what it printed and the path of the JSON results it wrote."""
        user_agents = ExampleUtils.read_user_agents(self.evidence_file)
        self.assertGreaterEqual(len(user_agents), count)
        evidence = os.path.join(self.folder, "evidence.yml")
        with open(evidence, "w", encoding="utf-8") as target:
            for user_agent in user_agents[:count]:
                target.write(f"---\nheader.user-agent: {user_agent}\n")
        results = os.path.join(self.folder, "results.json")

        finished = subprocess.run(
            [sys.executable, "-m", MODULE,
             "-d", self.data_file, "-e", evidence, "-j", results],
            capture_output=True, text=True, timeout=HANG_TIMEOUT_SECONDS)

        output = finished.stdout + finished.stderr
        self.assertEqual(0, finished.returncode, output)
        return output, results

    def test_runs_with_its_options(self):
        count = self.processes * USER_AGENTS_PER_PROCESS

        output, results = self.run_example(count)

        self.assertIn(f"Processing {count} user agents", output)
        with open(results, encoding="utf-8") as file:
            timings = json.load(file)
        self.assertGreater(timings["DetectionsPerSecond"], 0)
        self.assertGreater(timings["MsPerDetection"], 0)
        self.assertEqual(count, sum((counts(output) or {}).values()), output)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(performance.CONTACT_US), output)

    def test_runs_with_no_arguments(self):
        # As someone runs it from a fresh clone, so it finds the free Lite
        # file and the free file of evidence records for itself.
        environment = {name: value for name, value in os.environ.items()
                       if name not in SETTINGS}
        finished = subprocess.run(
            [sys.executable, "-m", MODULE],
            capture_output=True, text=True, env=environment,
            timeout=HANG_TIMEOUT_SECONDS)

        output = finished.stdout + finished.stderr
        self.assertEqual(0, finished.returncode, output)
        count = len(ExampleUtils.read_user_agents(self.evidence_file))
        self.assertGreater(count, 0)
        self.assertIn(f"Processing {count} user agents", output)
        self.assertEqual(count, sum((counts(output) or {}).values()), output)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(performance.CONTACT_US), output)
        self.assertIn("Find out more:", output)

    def test_runs_with_fewer_user_agents_than_processors(self):
        output, _ = self.run_example(1)

        self.assertEqual(1, sum((counts(output) or {}).values()), output)

    def test_counts_every_user_agent_when_they_do_not_divide_evenly(self):
        count = self.processes + 1

        output, _ = self.run_example(count)

        self.assertIn(f"Processing {count} user agents", output)
        self.assertEqual(count, sum((counts(output) or {}).values()), output)


class ReadUserAgentsTests(unittest.TestCase):
    """How the example reads the User-Agent of each evidence record. These
    need no data file."""

    def read(self, text):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, "evidence.yml")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return ExampleUtils.read_user_agents(path)

    def test_gives_the_user_agent_of_each_record_in_order(self):
        self.assertEqual(
            ["First/1.0 (a; b)", "Second/2.0"],
            self.read(
                "---\n"
                "header.user-agent: First/1.0 (a; b)\n"
                "header.sec-ch-ua-mobile: ?0\n"
                "---\n"
                "header.user-agent: Second/2.0\n"))

    def test_leaves_out_a_record_with_no_user_agent(self):
        self.assertEqual(
            ["Only/1.0"],
            self.read(
                "---\n"
                "header.sec-ch-ua-mobile: ?1\n"
                "---\n"
                "header.user-agent: Only/1.0\n"))

    def test_takes_the_quotes_off_a_quoted_user_agent(self):
        self.assertEqual(
            ["Quoted/1.0: yes", "Double/1.0"],
            self.read(
                "---\n"
                "header.user-agent: 'Quoted/1.0: yes'\n"
                "---\n"
                'header.User-Agent: "Double/1.0"\n'))

    def test_no_records_gives_an_empty_list(self):
        self.assertEqual([], self.read(""))


if __name__ == "__main__":
    unittest.main()

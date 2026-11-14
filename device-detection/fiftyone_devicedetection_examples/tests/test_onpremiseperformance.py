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
Runs the on-premise performance example as a person runs it, with python -m
and its -d, -u and -j options, on the free Lite data file and a short file
of User-Agents so that it takes seconds. Its work is done under
if __name__ == "__main__", in a separate process for each processor, so it
runs in a process of its own here.
"""

import ast
import itertools
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
    LITE_DATAFILE_NAME, UA_FILE_NAME

MODULE = "fiftyone_devicedetection_examples.onpremise.performance"

# The User-Agents each process is given when the example runs normally,
# enough to time detection without making the test slow.
USER_AGENTS_PER_PROCESS = 10

# Stops a run that never finishes. A run takes seconds, so this does not
# limit how fast the example has to be.
HANG_TIMEOUT_SECONDS = 300

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
        self.user_agents_file = ExampleUtils.find_file(UA_FILE_NAME)
        self.assertIsNotNone(
            self.data_file, f"{LITE_DATAFILE_NAME} was not found")
        self.assertIsNotNone(
            self.user_agents_file, f"{UA_FILE_NAME} was not found")
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        # The example starts one process for each processor.
        self.processes = multiprocessing.cpu_count()

    def run_example(self, count):
        """Runs the example on the first count User-Agents of the free
        file, copied as they are, and returns what it printed and the path
        of the JSON results it wrote."""
        user_agents = os.path.join(self.folder, "user-agents.csv")
        with open(self.user_agents_file, "rb") as source, \
                open(user_agents, "wb") as target:
            target.writelines(itertools.islice(source, count))
        results = os.path.join(self.folder, "results.json")

        finished = subprocess.run(
            [sys.executable, "-m", MODULE,
             "-d", self.data_file, "-u", user_agents, "-j", results],
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

    def test_runs_with_fewer_user_agents_than_processors(self):
        output, _ = self.run_example(1)

        self.assertEqual(1, sum((counts(output) or {}).values()), output)

    def test_counts_every_user_agent_when_they_do_not_divide_evenly(self):
        count = self.processes + 1

        output, _ = self.run_example(count)

        self.assertIn(f"Processing {count} user agents", output)
        self.assertEqual(count, sum((counts(output) or {}).values()), output)


if __name__ == "__main__":
    unittest.main()

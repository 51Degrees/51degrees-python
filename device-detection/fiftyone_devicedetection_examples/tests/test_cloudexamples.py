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

import inspect
import json5
import os
from pathlib import Path
import subprocess
import sys
import unittest
from fiftyone_devicedetection_examples.cloud.nativemodellookup_console import NativeModelLookupConsole
from fiftyone_devicedetection_examples.cloud.taclookup_console import TacLookupConsole
from fiftyone_devicedetection_examples.cloud.metadata_console import MetaDataConsole
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.cloud.gettingstarted_console import GettingStartedConsole
from fiftyone_devicedetection_examples.cloud.configurator_console import ConfiguratorConsole

# Text that shows an example printed a programming fault rather than a
# result. An example that reaches any of these is broken, however little of
# the data the resource key is entitled to.
FAULT_MARKERS = [
    "Traceback",
    "AttributeError",
    "TypeError",
    "KeyError",
    "Unknown ()",
    "Unknown (None)"
]


class DeviceDetectionExampleTests(unittest.TestCase):

    # Init method - specify a resource key here, or set one in the
    # environment variable named by ExampleUtils.RESOURCE_KEY_ENV_VAR.
    def setUp(self):
        self.resource_key = ExampleUtils.get_resource_key()
        self.logger = Logger()

        if not self.resource_key:
            # Skipping rather than passing, so a run without a key is not
            # mistaken for a run that proved something. The message names
            # the variable that was wanted.
            self.skipTest(ExampleUtils.get_missing_resource_key_message())

    def run_example(self, example):
        """!
        Run an example, collecting everything it writes through its output
        callback, and fail if any of it reads as a programming fault.
        """

        lines = []
        example(lines.append)
        output = "\n".join(str(line) for line in lines)

        self.assertGreater(len(lines), 0,
            "The example produced no output at all")

        for marker in FAULT_MARKERS:
            self.assertNotIn(marker, output,
                f"The example output contains '{marker}', which means it "
                f"failed rather than reporting a result. Output was:\n"
                f"{output}")

        return output

    def assert_device_lines_are_meaningful(self, output):
        """!
        Every device line the TAC and native model examples print must say
        something useful. Either it names a device, or it says the property
        has no value and gives the reason the cloud service supplied.
        """

        lines = [line for line in output.split("\n")
                 if line.startswith("\t")]

        self.assertGreater(len(lines), 0,
            "The example listed no devices and gave no reason for it")

        for line in lines:
            self.assertNotEqual("", line.strip(), "A device line is empty")

    def test_cloud_getting_started_console(self):
        example = GettingStartedConsole()
        configFile = Path(inspect.getfile(example.__class__)).parent.resolve().joinpath("gettingstarted_console.json").read_text()
        config = json5.loads(configFile)
        ExampleUtils.set_resource_key_in_config(config, self.resource_key)

        output = self.run_example(
            lambda out: example.run(config, self.logger, out))

        self.assertIn("Input values:", output)
        self.assertIn("Mobile Device:", output)

    def test_cloud_nativemodellookup_console(self):
        example = NativeModelLookupConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assertIn(
            "Which devices are associated with the native model name "
            "'SC-03L'?", output)
        self.assert_device_lines_are_meaningful(output)

    def test_cloud_taclookup_console(self):
        example = TacLookupConsole()
        configFile = Path(inspect.getfile(example.__class__)).parent.resolve().joinpath("taclookup_console.json").read_text()
        config = json5.loads(configFile)
        ExampleUtils.set_resource_key_in_config(config, self.resource_key)

        output = self.run_example(
            lambda out: example.run(config, self.logger, out))

        self.assertIn(
            "Which devices are associated with the TAC '35925406'?", output)
        self.assert_device_lines_are_meaningful(output)

    def test_cloud_metadata_console(self):
        example = MetaDataConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assertIn("Accepted evidence keys:", output)
        self.assertIn("Property - ", output)

    def test_cloud_configurator_console(self):
        example = ConfiguratorConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assertIn("device.ismobile: ", output)
        self.assertNotEqual("device.ismobile:", output.strip())

    def test_cloud_failuretomatch(self):
        """The failure to match example is a script rather than a class,
        so it is run as one. It is run with the current resource key
        variable only, because it read the older name alone and told
        anyone using the current one that no key was set."""

        example = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "src", "fiftyone_devicedetection_examples", "cloud",
            "failuretomatch.py")
        environment = dict(os.environ)
        environment.pop(ExampleUtils.LEGACY_RESOURCE_KEY_ENV_VAR, None)
        environment[ExampleUtils.RESOURCE_KEY_ENV_VAR] = self.resource_key

        finished = subprocess.run(
            [sys.executable, example], capture_output=True, text=True,
            env=environment, timeout=120)

        output = finished.stdout + finished.stderr
        self.assertEqual(0, finished.returncode, output)
        self.assertNotIn("No resource key found", output)
        self.assertIn("a mobile device?", output)
        for marker in FAULT_MARKERS:
            self.assertNotIn(marker, output)

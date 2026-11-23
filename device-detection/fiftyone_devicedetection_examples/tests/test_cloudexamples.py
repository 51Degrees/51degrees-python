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

from .live_cloud import find_resource_key, no_resource_key

NO_KEY = no_resource_key(
    "the device product, and the hardware product for the lookups",
    "device detection properties, and for the hardware profiles the TAC "
    "and native model lookups return", several=True)

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

# What the TAC and native model examples print in place of their lookups
# when the resource key does not carry the hardware lookup.
NO_HARDWARE_LOOKUP = "does not include HardwarePlatform.Profiles"

# The values the TAC and native model examples look up.
TACS = ("35925406", "86386802")
NATIVE_MODELS = ("SC-03L", "iPhone11,8")

# What ExampleUtils.get_human_readable gives for a property with no value,
# alone or followed by the reason in parentheses.
NO_VALUE = "Unknown"


def is_value(text):
    """Whether the text is a value rather than empty or the rendering of a
    property with no value."""
    return (text != "" and text != NO_VALUE
            and not text.startswith(NO_VALUE + " ("))


def vendor_and_model(line):
    """The vendor and model of a device line, which has the form
    '<vendor> <name> (<model>)', or None when the line has another form.
    The vendor is the text before the first space, and the model the text
    inside the final parentheses, which may hold parentheses of their own
    when it has no value and gives the reason."""
    text = line.strip()
    if not text.endswith(")"):
        return None
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                break
    else:
        return None
    before = text[:index].strip()
    if before == "":
        return None
    return before.split(" ", 1)[0], text[index + 1:-1].strip()


def lines_under(output, heading):
    """The tab-indented lines printed straight after the heading, or None
    when the heading was not printed."""
    lines = output.split("\n")
    if heading not in lines:
        return None
    under = []
    for line in lines[lines.index(heading) + 1:]:
        if not line.startswith("\t"):
            break
        under.append(line)
    return under


class DeviceDetectionExampleTests(unittest.TestCase):

    def setUp(self):
        self.resource_key = find_resource_key()
        self.logger = Logger()

        if not self.resource_key:
            self.skipTest(NO_KEY)

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

    def assert_lists_devices(self, output, lookup, kind, values):
        """!
        Fail unless the TAC or native model example listed, for each value
        it looked up, at least one device with a vendor and a model. lookup
        names the lookup for the message when the resource key does not
        carry it, and kind names what each value is, as the example's
        heading does.
        """

        if NO_HARDWARE_LOOKUP in output:
            self.fail(
                "The resource key in _51DEGREES_RESOURCE_KEY_BESPOKE does "
                "not include HardwarePlatform.Profiles, which the "
                f"{lookup} needs.\n{output}")

        for value in values:
            heading = f"Which devices are associated with the {kind} '{value}'?"
            devices = [vendor_and_model(line)
                       for line in lines_under(output, heading) or []]
            if not any(device and is_value(device[0]) and is_value(device[1])
                       for device in devices):
                self.fail(
                    "No device with a vendor and a model was listed for the "
                    f"{kind} '{value}'.\n{output}")

    def test_cloud_getting_started_console(self):
        example = GettingStartedConsole()
        configFile = Path(inspect.getfile(example.__class__)).parent.resolve().joinpath("gettingstarted_console.json").read_text()
        config = json5.loads(configFile)
        ExampleUtils.set_resource_key_in_config(config, self.resource_key)

        output = self.run_example(
            lambda out: example.run(config, self.logger, out))

        self.assertIn("Input values:", output)
        self.assertIn("Mobile Device:", output)
        self.assertIn("Find out more:", output)

    def test_cloud_nativemodellookup_console(self):
        example = NativeModelLookupConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assert_lists_devices(
            output, "native model lookup", "native model name", NATIVE_MODELS)
        self.assertIn("Find out more:", output)

    def test_cloud_taclookup_console(self):
        example = TacLookupConsole()
        configFile = Path(inspect.getfile(example.__class__)).parent.resolve().joinpath("taclookup_console.json").read_text()
        config = json5.loads(configFile)
        ExampleUtils.set_resource_key_in_config(config, self.resource_key)

        output = self.run_example(
            lambda out: example.run(config, self.logger, out))

        self.assert_lists_devices(output, "TAC lookup", "TAC", TACS)
        self.assertIn("Find out more:", output)

    def test_cloud_metadata_console(self):
        example = MetaDataConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assertIn("Accepted evidence keys:", output)
        self.assertIn("Property - ", output)
        self.assertIn("Find out more:", output)

    def test_cloud_configurator_console(self):
        example = ConfiguratorConsole()

        output = self.run_example(
            lambda out: example.run(self.resource_key, self.logger, out))

        self.assertIn("device.ismobile: ", output)
        self.assertNotEqual("device.ismobile:", output.strip())
        self.assertIn("Find out more:", output)

    def test_cloud_failuretomatch(self):
        """The failure to match example is a script rather than a class,
        so it is run as one, with the resource key in its environment."""

        example = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "src", "fiftyone_devicedetection_examples", "cloud",
            "failuretomatch.py")
        environment = dict(os.environ)
        environment[ExampleUtils.RESOURCE_KEY_ENV_VAR] = self.resource_key

        finished = subprocess.run(
            [sys.executable, example], capture_output=True, text=True,
            env=environment, timeout=120)

        output = finished.stdout + finished.stderr
        self.assertEqual(0, finished.returncode, output)
        self.assertNotIn("No resource key found", output)
        self.assertIn("a mobile device?", output)
        self.assertIn("Find out more:", output)
        for marker in FAULT_MARKERS:
            self.assertNotIn(marker, output)

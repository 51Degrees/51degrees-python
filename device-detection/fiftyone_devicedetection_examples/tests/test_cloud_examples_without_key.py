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

"""
Runs each cloud example as it runs from a fresh clone, with no resource key
set. Each must end without an error, naming the environment variable to set
and giving a tagged link to the page where a key is created.
"""

import io
import logging
import os
import runpy
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.cloud import configurator_console
from fiftyone_devicedetection_examples.cloud import gettingstarted_console
from fiftyone_devicedetection_examples.cloud import metadata_console
from fiftyone_devicedetection_examples.cloud import nativemodellookup_console
from fiftyone_devicedetection_examples.cloud import taclookup_console
from fiftyone_devicedetection_examples.cloud.gettingstarted_web import (
    app as gettingstarted_web)
from fiftyone_devicedetection_examples.cloud.useragentclienthints_web import (
    app as useragentclienthints_web)

# Every name a key can be read from, which a fresh clone does not set.
KEY_SETTINGS = [
    "_51DEGREES_RESOURCE_KEY", "resource_key", "RESOURCE_KEY",
    "_51DEGREES_LICENSE_KEY", "license_key"]

# A link to the page where a resource key is created, with the campaign
# tags every example's links carry.
CONFIGURE_LINK = (
    r"https://51degrees\.com/configure[^\s?]*\?utm_source=code"
    r"&utm_medium=example&utm_campaign=51degrees-python&utm_content=")


class Recorder(logging.Handler):
    """Keeps every message logged while it is attached."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def run_without_key(run):
    """Runs an example with no key in the environment, and returns what it
    printed and logged."""
    printed = io.StringIO()
    recorder = Recorder()
    root = logging.getLogger()
    root.addHandler(recorder)
    try:
        with mock.patch.dict(os.environ), redirect_stdout(printed):
            for name in KEY_SETTINGS:
                os.environ.pop(name, None)
            run()
    finally:
        root.removeHandler(recorder)
    return printed.getvalue() + "\n".join(recorder.messages)


class CloudExamplesWithoutKeyTests(unittest.TestCase):

    def assert_says_how_to_get_a_key(self, said, names_variable=True):
        self.assertRegex(said, CONFIGURE_LINK)
        if names_variable:
            self.assertIn(ExampleUtils.RESOURCE_KEY_ENV_VAR, said)

    def test_configurator_console(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: configurator_console.main([])))

    def test_gettingstarted_console(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: gettingstarted_console.main([])))

    def test_metadata_console(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: metadata_console.main([])))

    def test_nativemodellookup_console(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: nativemodellookup_console.main([])))

    def test_taclookup_console(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: taclookup_console.main([])))

    def test_gettingstarted_web(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: gettingstarted_web.main([])))

    def test_useragentclienthints_web(self):
        self.assert_says_how_to_get_a_key(
            run_without_key(lambda: useragentclienthints_web.main([])))

    def test_failuretomatch(self):
        # This example has no main and runs when it is run as a script.
        self.assert_says_how_to_get_a_key(run_without_key(
            lambda: runpy.run_module(
                "fiftyone_devicedetection_examples.cloud.failuretomatch",
                run_name="__main__")))


if __name__ == "__main__":
    unittest.main()

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
Runs the mixed cloud console and web examples as they run from a fresh
clone, with no key set. Each must end without an error, naming the
environment variables to set and giving a tagged link to the page where a
key is created.
"""

import io
import logging
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_pipeline_examples.cloud.mixed import gettingstarted_console
from fiftyone_pipeline_examples.cloud.mixed.gettingstarted_web import app
from fiftyone_pipeline_examples.example_utils import ExampleUtils

# Every name a key can be read from, which a fresh clone does not set.
KEY_SETTINGS = [
    "_51DEGREES_RESOURCE_KEY",
    "_51DEGREES_LICENSE_KEY"]

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


class MixedExamplesWithoutKeyTests(unittest.TestCase):

    def run_without_key(self, main):
        """Runs main with no arguments and no key in the environment, fails
        the test if it exits, and returns what it printed and logged."""
        printed = io.StringIO()
        recorder = Recorder()
        root = logging.getLogger()
        root.addHandler(recorder)
        try:
            with mock.patch.dict(os.environ), redirect_stdout(printed):
                for name in KEY_SETTINGS:
                    os.environ.pop(name, None)
                try:
                    main([])
                except SystemExit as stopped:
                    self.fail(f"The example exited with {stopped.code!r}")
        finally:
            root.removeHandler(recorder)
        return printed.getvalue() + "\n".join(recorder.messages)

    def test_says_how_to_get_a_key(self):
        said = self.run_without_key(gettingstarted_console.main)
        self.assertIn(ExampleUtils.RESOURCE_KEY_ENV_VAR, said)
        self.assertRegex(said, CONFIGURE_LINK)

    def test_web_says_how_to_get_a_key_and_ends(self):
        started = AssertionError("The web server was started")
        with mock.patch.object(app, "create_app", side_effect=started):
            said = self.run_without_key(app.main)
        self.assertIn(ExampleUtils.RESOURCE_KEY_ENV_VAR, said)
        self.assertRegex(said, CONFIGURE_LINK)


if __name__ == "__main__":
    unittest.main()

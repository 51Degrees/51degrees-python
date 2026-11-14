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

# Runs the cloud countries example as it runs from a fresh clone, with no
# resource key set. It must end without an error, name the environment
# variable to set, give the tagged link to the page where a key is created,
# and end with its Find out more section.

import io
import logging
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_ipintelligence_examples.cloud import countries_console
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils

KEY_SETTINGS = [
    "_51DEGREES_RESOURCE_KEY", "resource_key", "RESOURCE_KEY",
    "_51DEGREES_LICENSE_KEY", "license_key"]

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


def run_without_key():
    """Runs the example's main with no key in the environment, and returns
    what it logged followed by what it printed."""
    printed = io.StringIO()
    recorder = Recorder()
    root = logging.getLogger()
    root.addHandler(recorder)
    try:
        with mock.patch.dict(os.environ), redirect_stdout(printed):
            for name in KEY_SETTINGS:
                os.environ.pop(name, None)
            countries_console.main([])
    finally:
        root.removeHandler(recorder)
    return "\n".join(recorder.messages) + "\n" + printed.getvalue()


class CountriesCloudWithoutKeyTests(unittest.TestCase):

    def test_says_how_to_get_a_key(self):
        said = run_without_key()
        self.assertIn(ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR, said)
        self.assertRegex(said, CONFIGURE_LINK)

    def test_ends_with_find_out_more(self):
        said = run_without_key()
        self.assertIn("Find out more:", said)
        for _, url in countries_console.FIND_OUT_MORE:
            self.assertIn(url, said)

    def test_names_no_native_engine(self):
        # The example uses the cloud service only, so it does not point at
        # the repository of the native engine.
        for _, url in countries_console.FIND_OUT_MORE:
            self.assertNotIn("51degrees-cxx", url)


if __name__ == "__main__":
    unittest.main()

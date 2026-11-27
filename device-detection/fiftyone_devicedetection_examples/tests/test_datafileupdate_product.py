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

# The data file update example names a product to the 51Degrees distributor
# only when it is given one. With none given it names none, so a license key
# that holds one product is served that product. No pipeline is built and
# nothing is downloaded, so these tests need no license key and no data
# file.

import os
import tempfile
import unittest
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise import datafileupdate_console
from fiftyone_pipeline_core.logger import Logger

# Stands in for a license key. No request is made with it.
KEY = "ABCDEFGHIJKL"


class Stop(Exception):
    """Ends the example where it would build the pipeline that updates the
    data file."""


def settings_given(*product):
    """Runs the example to the point where it builds the pipeline that
    updates the data file, and returns the settings it gave the pipeline
    builder. The data file is one that does not exist, in a directory that
    does, so the example builds no other pipeline first."""
    builder = mock.Mock(side_effect=Stop())
    with tempfile.TemporaryDirectory() as directory:
        location = os.path.join(directory, "not-there.hash")
        with mock.patch.object(
                datafileupdate_console, "DeviceDetectionPipelineBuilder",
                builder), mock.patch.object(
                ExampleUtils, "find_file", return_value=location):
            try:
                datafileupdate_console.DataFileUpdateConsole().run(
                    location, KEY, False, Logger(min_level="error"),
                    lambda text: None, *product)
            except Stop:
                pass
    if builder.call_count != 1:
        raise AssertionError(
            "The example built " + str(builder.call_count) + " pipelines")
    return builder.call_args[1]


class DataFileUpdateProductTests(unittest.TestCase):

    def test_a_product_given_is_the_product_asked_for(self):
        settings = settings_given("V4TAC")
        self.assertEqual("V4TAC", settings["data_update_product_type"])
        self.assertEqual(KEY, settings["licence_keys"])

    def test_no_product_is_asked_for_when_none_is_given(self):
        for name, product in (
                ("no argument", ()), ("none", (None,)), ("empty", ("",))):
            with self.subTest(name):
                self.assertIsNone(
                    settings_given(*product).get("data_update_product_type"))

    def test_the_third_argument_is_the_product(self):
        for name, argv, product in (
                ("given", [KEY, "a.hash", "V4TAC"], "V4TAC"),
                ("not given", [KEY, "a.hash"], None)):
            with self.subTest(name):
                with mock.patch.object(
                        datafileupdate_console.DataFileUpdateConsole,
                        "run") as run, mock.patch.object(
                        ExampleUtils, "print_find_out_more"):
                    datafileupdate_console.main(argv)
                self.assertEqual(product, run.call_args[0][-1])


if __name__ == "__main__":
    unittest.main()

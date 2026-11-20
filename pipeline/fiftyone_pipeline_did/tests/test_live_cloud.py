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

"""Checks live_cloud.py, which every test folder that reads a setting from
the environment holds a copy of. These need no resource key.
"""

import os
import unittest
from pathlib import Path
from unittest import mock

from . import live_cloud

# Every folder that holds a copy of live_cloud.py, from the root of the
# repository.
COPIES = (
    "device-detection/fiftyone_devicedetection_cloud/tests",
    "device-detection/fiftyone_devicedetection_examples/tests",
    "ip-intelligence/fiftyone_ipintelligence_examples/tests",
    "ip-intelligence/fiftyone_ipintelligence_onpremise/tests",
    "location/tests",
    "pipeline/fiftyone_pipeline_cloudrequestengine/examples/tests",
    "pipeline/fiftyone_pipeline_cloudrequestengine/tests",
    "pipeline/fiftyone_pipeline_did/tests",
)

NAMES = (
    "_51DEGREES_RESOURCE_KEY", "_51DEGREES_RESOURCE_KEY_BESPOKE",
    "_51DEGREES_RESOURCE_KEY_BASIC", "_51DEGREES_LICENSE_KEY")


class ReadTests(unittest.TestCase):

    def setUp(self):
        # Each test starts with none of the names set, and what it sets is
        # put back afterwards.
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for name in NAMES:
            os.environ.pop(name, None)

    def test_resource_key_is_found(self):
        os.environ["_51DEGREES_RESOURCE_KEY"] = "new-key"
        self.assertEqual("new-key", live_cloud.find_resource_key())

    def test_no_resource_key_gives_none(self):
        self.assertIsNone(live_cloud.find_resource_key())

    def test_a_variable_is_read(self):
        os.environ["_51DEGREES_LICENSE_KEY"] = "new-licence"
        self.assertEqual(
            "new-licence",
            live_cloud.read_environment("_51DEGREES_LICENSE_KEY"))

    def test_an_unset_variable_gives_none(self):
        self.assertIsNone(
            live_cloud.read_environment("_51DEGREES_LICENSE_KEY"))

    def test_a_variable_set_to_nothing_counts_as_set(self):
        os.environ["_51DEGREES_LICENSE_KEY"] = ""
        self.assertTrue(live_cloud.is_set("_51DEGREES_LICENSE_KEY"))

    def test_an_unset_variable_is_not_set(self):
        self.assertFalse(live_cloud.is_set("_51DEGREES_LICENSE_KEY"))

class CopiesTests(unittest.TestCase):

    def test_every_copy_is_the_same_file(self):
        # One copy is tested here, so the others have to be that file.
        root = Path(__file__).resolve().parents[3]
        if not (root / "ci" / "packages.json").is_file():
            self.skipTest("not run from a checkout of the repository")
        expected = Path(__file__).with_name("live_cloud.py").read_bytes()
        for folder in COPIES:
            with self.subTest(folder=folder):
                copy = root / folder / "live_cloud.py"
                self.assertTrue(copy.is_file(), str(copy))
                self.assertEqual(expected, copy.read_bytes())


if __name__ == "__main__":
    unittest.main()

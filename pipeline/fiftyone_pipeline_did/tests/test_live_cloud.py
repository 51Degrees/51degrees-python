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
the environment holds a copy of. A variable whose name changed is still
read under its old name when the new one is not set, and using the old name
prints once that it is deprecated. These need no resource key.
"""

import contextlib
import io
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
    "_51DEGREES_RESOURCE_KEY_BASIC", "resource_key",
    "_51DEGREES_LICENSE_KEY", "license_key")


class OldNameTests(unittest.TestCase):

    def setUp(self):
        # Each test starts with none of the names set and no old name
        # reported yet, and what it sets is put back afterwards.
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for name in NAMES:
            os.environ.pop(name, None)
        reported = mock.patch.object(
            live_cloud, "_reported_old_names", set())
        reported.start()
        self.addCleanup(reported.stop)

    def printed(self, call):
        """What a call returned and what it printed to the error stream."""
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            value = call()
        return value, errors.getvalue()

    def test_resource_key_is_read_from_the_old_name(self):
        os.environ["resource_key"] = "old-key"
        value, errors = self.printed(live_cloud.find_resource_key)
        self.assertEqual("old-key", value)
        self.assertIn("resource_key environment variable is deprecated",
                      errors)
        self.assertIn("_51DEGREES_RESOURCE_KEY", errors)

    def test_new_resource_key_name_wins_and_nothing_is_printed(self):
        os.environ["_51DEGREES_RESOURCE_KEY"] = "new-key"
        os.environ["resource_key"] = "old-key"
        value, errors = self.printed(live_cloud.find_resource_key)
        self.assertEqual("new-key", value)
        self.assertEqual("", errors)

    def test_no_resource_key_gives_none(self):
        value, errors = self.printed(live_cloud.find_resource_key)
        self.assertIsNone(value)
        self.assertEqual("", errors)

    def test_other_names_do_not_fall_back_to_the_old_name(self):
        # The old name was one key, so a search for a key of another tier
        # does not take it.
        os.environ["resource_key"] = "old-key"
        value, _ = self.printed(lambda: live_cloud.find_resource_key(
            ("_51DEGREES_RESOURCE_KEY_BASIC",)))
        self.assertIsNone(value)

    def test_old_name_is_read_and_reported_once(self):
        os.environ["license_key"] = "old-licence"

        def twice():
            return (
                live_cloud.read_environment(
                    "_51DEGREES_LICENSE_KEY", "license_key"),
                live_cloud.read_environment(
                    "_51DEGREES_LICENSE_KEY", "license_key"))

        value, errors = self.printed(twice)
        self.assertEqual(("old-licence", "old-licence"), value)
        self.assertEqual(
            1, errors.count("license_key environment variable is deprecated"))
        self.assertIn("_51DEGREES_LICENSE_KEY", errors)

    def test_old_name_is_read_when_the_new_one_is_empty(self):
        os.environ["_51DEGREES_LICENSE_KEY"] = ""
        os.environ["license_key"] = "old-licence"
        value, _ = self.printed(lambda: live_cloud.read_environment(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertEqual("old-licence", value)

    def test_new_name_wins_and_nothing_is_printed(self):
        os.environ["_51DEGREES_LICENSE_KEY"] = "new-licence"
        os.environ["license_key"] = "old-licence"
        value, errors = self.printed(lambda: live_cloud.read_environment(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertEqual("new-licence", value)
        self.assertEqual("", errors)

    def test_neither_name_gives_none(self):
        value, errors = self.printed(lambda: live_cloud.read_environment(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertIsNone(value)
        self.assertEqual("", errors)

    def test_old_name_set_to_nothing_still_counts_as_set(self):
        # A switch is on when its variable is set, whatever it holds.
        os.environ["license_key"] = ""
        value, errors = self.printed(lambda: live_cloud.is_set(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertTrue(value)
        self.assertEqual(
            1, errors.count("license_key environment variable is deprecated"))
        self.assertIn("_51DEGREES_LICENSE_KEY", errors)

    def test_new_name_set_to_nothing_counts_as_set(self):
        os.environ["_51DEGREES_LICENSE_KEY"] = ""
        value, errors = self.printed(lambda: live_cloud.is_set(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertTrue(value)
        self.assertEqual("", errors)

    def test_neither_name_is_not_set(self):
        value, errors = self.printed(lambda: live_cloud.is_set(
            "_51DEGREES_LICENSE_KEY", "license_key"))
        self.assertFalse(value)
        self.assertEqual("", errors)


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

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

"""Checks that the example helper still reads each setting under the name
its environment variable had before, when the new name is not set, and
prints once that the old name is deprecated. These need no resource key.
"""

import contextlib
import io
import os
import unittest
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.key_utils import KeyUtils

# Each reader, with the new name of its variable and the old one.
PAIRS = {
    "get_resource_key": ("_51DEGREES_RESOURCE_KEY", "resource_key"),
    "get_license_key": ("_51DEGREES_LICENSE_KEY", "license_key"),
    "get_cloud_endpoint": ("_51DEGREES_CLOUD_ENDPOINT", "cloud_endpoint"),
    "get_data_file_path": ("_51DEGREES_DD_PATH", "51DEGREES_DD_PATH"),
}

# Each constant that names a variable, with the value it has to hold. The
# ones that held an old name hold it still.
CONSTANTS = {
    "RESOURCE_KEY_ENV_VAR": "_51DEGREES_RESOURCE_KEY",
    "LEGACY_RESOURCE_KEY_ENV_VAR": "resource_key",
    "LICENSE_KEY_ENV_VAR": "_51DEGREES_LICENSE_KEY",
    "LEGACY_LICENSE_KEY_ENV_VAR": "license_key",
    "CLOUD_ENDPOINT_ENV_VAR": "_51DEGREES_CLOUD_ENDPOINT",
    "ENDPOINT_ENV_VAR": "cloud_endpoint",
    "DD_PATH_ENV_VAR": "_51DEGREES_DD_PATH",
    "DATA_FILE_ENV_VAR": "51DEGREES_DD_PATH",
}


class OldNameTests(unittest.TestCase):

    def setUp(self):
        # Each test starts with none of the names set and no old name
        # reported yet, and what it sets is put back afterwards.
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for pair in PAIRS.values():
            for name in pair:
                os.environ.pop(name, None)
                os.environ.pop(name.upper(), None)
        reported = mock.patch.object(
            ExampleUtils, "_ExampleUtils__reported_old_names", set(),
            create=True)
        reported.start()
        self.addCleanup(reported.stop)

    def printed(self, call):
        """What a call returned and what it printed to the error stream."""
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            value = call()
        return value, errors.getvalue()

    def test_each_setting_is_read_from_its_old_name(self):
        for getter, (name, old_name) in PAIRS.items():
            with self.subTest(getter=getter):
                os.environ[old_name] = "old-value"
                value, errors = self.printed(getattr(ExampleUtils, getter))
                self.assertEqual("old-value", value)
                self.assertIn(
                    old_name + " environment variable is deprecated", errors)
                self.assertIn(name, errors)
                del os.environ[old_name]

    def test_new_name_wins_and_nothing_is_printed(self):
        for getter, (name, old_name) in PAIRS.items():
            with self.subTest(getter=getter):
                os.environ[name] = "new-value"
                os.environ[old_name] = "old-value"
                value, errors = self.printed(getattr(ExampleUtils, getter))
                self.assertEqual("new-value", value)
                self.assertEqual("", errors)
                del os.environ[name]
                del os.environ[old_name]

    def test_neither_name_gives_nothing(self):
        for getter in PAIRS:
            with self.subTest(getter=getter):
                value, errors = self.printed(getattr(ExampleUtils, getter))
                self.assertFalse(value)
                self.assertEqual("", errors)

    def test_old_name_is_reported_once(self):
        getter, (name, old_name) = next(iter(PAIRS.items()))
        os.environ[old_name] = "old-value"

        def twice():
            return (getattr(ExampleUtils, getter)(),
                    getattr(ExampleUtils, getter)())

        value, errors = self.printed(twice)
        self.assertEqual(("old-value", "old-value"), value)
        self.assertEqual(
            1, errors.count(old_name + " environment variable is deprecated"))

    def test_constants_hold_the_old_and_the_new_names(self):
        for constant, value in CONSTANTS.items():
            with self.subTest(constant=constant):
                self.assertEqual(value, getattr(ExampleUtils, constant))

    def test_licence_key_is_read_from_the_old_name_in_upper_case(self):
        os.environ.pop("LICENSE_KEY", None)
        os.environ["LICENSE_KEY"] = "old-value"
        value, _ = self.printed(ExampleUtils.get_license_key)
        self.assertEqual("old-value", value)


class KeyUtilsTests(unittest.TestCase):

    LOWER = "_51degrees_test_named_key"
    UPPER = "_51DEGREES_TEST_NAMED_KEY"

    def setUp(self):
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(self.LOWER, None)
        os.environ.pop(self.UPPER, None)

    def test_key_is_read_from_the_name_given(self):
        os.environ[self.LOWER] = "value"
        self.assertEqual("value", KeyUtils.get_named_key(self.LOWER))

    def test_key_is_read_from_the_name_in_upper_case(self):
        os.environ[self.UPPER] = "value"
        self.assertEqual("value", KeyUtils.get_named_key(self.LOWER))

    def test_missing_key_gives_none(self):
        self.assertIsNone(KeyUtils.get_named_key(self.LOWER))


if __name__ == "__main__":
    unittest.main()

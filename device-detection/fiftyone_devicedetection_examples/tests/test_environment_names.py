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

"""Checks that the constants of the example helper that name a variable keep
their values, including those that hold a name that is no longer read.
"""

import os
import unittest
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.key_utils import KeyUtils

# Each constant that names a variable, with the value it has to hold. The
# ones that held an old name hold it still, although it is no longer read.
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


class ConstantTests(unittest.TestCase):

    def test_constants_hold_the_old_and_the_new_names(self):
        for constant, value in CONSTANTS.items():
            with self.subTest(constant=constant):
                self.assertEqual(value, getattr(ExampleUtils, constant))


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

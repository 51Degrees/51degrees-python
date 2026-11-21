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

import unittest


from fiftyone_ipintelligence_examples.example_utils import ExampleUtils


# Each constant that names a variable, with the value it has to hold. The
# ones that held an old name hold it still, although it is no longer read.
CONSTANTS = {
    "CLOUD_RESOURCE_KEY_ENV_VAR": "_51DEGREES_RESOURCE_KEY",
    "RESOURCE_KEY_ENV_VAR": "resource_key",
    "LICENSE_KEY_ENV_VAR": "_51DEGREES_LICENSE_KEY",
    "LEGACY_LICENSE_KEY_ENV_VAR": "license_key",
    "CLOUD_ENDPOINT_ENV_VAR": "_51DEGREES_CLOUD_ENDPOINT",
    "ENDPOINT_ENV_VAR": "cloud_endpoint",
    "IPI_PATH_ENV_VAR": "_51DEGREES_IPI_PATH",
    "DATA_FILE_ENV_VAR": "IPINTELLIGENCEDATAFILE",
}


class ConstantTests(unittest.TestCase):

    def test_constants_hold_the_old_and_the_new_names(self):
        for constant, value in CONSTANTS.items():
            with self.subTest(constant=constant):
                self.assertEqual(value, getattr(ExampleUtils, constant))


if __name__ == "__main__":
    unittest.main()

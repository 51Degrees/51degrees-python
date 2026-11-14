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
The two profile metadata examples run as they run from a fresh clone, with
no arguments, on the free Lite data file. Each writes the hardware profiles
as JSON to standard output, and to standard error says which properties
need the Enterprise data file, with the link to ask for a copy, and ends
with Find out more.
"""

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from fiftyone_devicedetection_examples.onpremise import csv_profile_metadata
from fiftyone_devicedetection_examples.onpremise import (
    profile_metadata_console)

# The settings the examples read, which a fresh clone does not have.
SETTINGS = ["_51DEGREES_LICENSE_KEY", "license_key", "LICENSE_KEY"]


def run_example(main):
    """Runs an example's main with no arguments and the settings taken out
    of the environment, and returns what it wrote to standard output and to
    standard error."""
    out = io.StringIO()
    err = io.StringIO()
    with mock.patch.dict(os.environ), redirect_stdout(out), \
            redirect_stderr(err):
        for name in SETTINGS:
            os.environ.pop(name, None)
        main([])
    return out.getvalue(), err.getvalue()


class ProfileMetadataOnTheFreeFileTests(unittest.TestCase):

    def assert_lists_profiles(self, out):
        profiles = json.loads(out)
        self.assertTrue(profiles, "no hardware profiles were listed")
        self.assertIn("profileId", profiles[0])

    def test_profile_metadata_console(self):
        out, err = run_example(profile_metadata_console.main)
        self.assert_lists_profiles(out)
        self.assertIn("which only the Enterprise data file has", err)
        self.assertIn(profile_metadata_console.CONTACT_US, err)
        self.assertIn("Find out more:", err)

    def test_csv_profile_metadata_without_the_export(self):
        out, err = run_example(csv_profile_metadata.main)
        self.assert_lists_profiles(out)
        self.assertIn(csv_profile_metadata.CSV_FILE_NAME, err)
        # One contact link, tagged with this example, so that an enquiry is
        # counted against the example that prompted it.
        self.assertEqual(1, err.count(csv_profile_metadata.CONTACT_US), err)
        self.assertNotIn(profile_metadata_console.CONTACT_US, err)
        self.assertIn("which only the Enterprise data file has", err)
        self.assertIn("Find out more:", err)


if __name__ == "__main__":
    unittest.main()

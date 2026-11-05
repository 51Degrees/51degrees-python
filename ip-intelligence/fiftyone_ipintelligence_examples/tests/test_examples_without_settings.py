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

# Runs the on-premise examples as they run from a fresh clone, with no data
# file setting and no licence key, so that they use the free data files.
# Each must finish, show the properties only the Enterprise data file has as
# needing it, and give the link to ask for a copy.

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.onpremise import compare_console
from fiftyone_ipintelligence_examples.onpremise import countries_console
from fiftyone_ipintelligence_examples.onpremise import datafileupdate_console
from fiftyone_ipintelligence_examples.onpremise import gettingstarted_console
from fiftyone_ipintelligence_examples.onpremise import metadata_console
from fiftyone_ipintelligence_examples.onpremise import mixed_console
from fiftyone_ipintelligence_examples.onpremise import offlineprocessing
from fiftyone_ipintelligence_examples.onpremise import performance_console

# The settings the examples read, which a fresh clone does not have.
SETTINGS = ["license_key", "LICENSE_KEY", ExampleUtils.DATA_FILE_ENV_VAR]

# Options that keep the performance example short. They leave the data file
# to the example.
PERFORMANCE_OPTIONS = ["--record_limit", "200", "--workers", "1"]

# The mixed example combines IP intelligence with device detection, which
# is an optional dependency.
try:
    import fiftyone_devicedetection_onpremise  # noqa: F401
    device_detection_available = True
except ImportError:
    device_detection_available = False


def run_without_settings(main, argv=None):
    """Runs an example's main with the settings taken out of the
    environment, and returns what it printed."""
    printed = io.StringIO()
    with mock.patch.dict(os.environ), redirect_stdout(printed):
        for name in SETTINGS:
            os.environ.pop(name, None)
        main(argv or [])
    return printed.getvalue()


class ExamplesWithoutSettingsTests(unittest.TestCase):

    def test_gettingstarted_console(self):
        printed = run_without_settings(gettingstarted_console.main)
        self.assertIn("Country: " + ExampleUtils.NEEDS_ENTERPRISE, printed)
        self.assertIn(
            ExampleUtils.get_enterprise_note(gettingstarted_console.CONTACT_US),
            printed)

    def test_countries_console(self):
        printed = run_without_settings(countries_console.main)
        self.assertIn(
            "Listing the countries an IP address is most likely in needs the "
            "CountryCodesGeographical and CountryCodesPopulation properties",
            printed)
        self.assertIn(countries_console.CONTACT_US, printed)

    def test_metadata_console(self):
        printed = run_without_settings(metadata_console.main)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(metadata_console.CONTACT_US),
            printed)

    def test_offlineprocessing(self):
        printed = run_without_settings(offlineprocessing.main)
        self.assertIn("ip.country: " + ExampleUtils.NEEDS_ENTERPRISE, printed)
        self.assertIn(
            "# " + ExampleUtils.get_enterprise_note(
                offlineprocessing.CONTACT_US),
            printed)

    def test_compare_console(self):
        printed = run_without_settings(compare_console.main)
        self.assertIn(
            "Comparing known locations with IP Intelligence needs the "
            "Latitude, Longitude, LocationConfidence and Country properties",
            printed)
        self.assertIn(compare_console.CONTACT_US, printed)

    def test_performance_console(self):
        printed = run_without_settings(
            performance_console.main, PERFORMANCE_OPTIONS)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(performance_console.CONTACT_US),
            printed)

    def test_datafileupdate_console(self):
        printed = run_without_settings(datafileupdate_console.main)
        self.assertIn("The data file in use is the", printed)
        self.assertIn(datafileupdate_console.CONTACT_US, printed)

    @unittest.skipUnless(
        device_detection_available, "device detection is not installed")
    def test_mixed_console(self):
        printed = run_without_settings(mixed_console.main)
        self.assertIn(ExampleUtils.NEEDS_ENTERPRISE, printed)
        self.assertIn(
            ExampleUtils.get_enterprise_note(mixed_console.CONTACT_US),
            printed)


if __name__ == "__main__":
    unittest.main()

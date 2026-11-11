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

# Runs the on-premise examples as they run from a fresh clone, with no
# arguments and no licence key, so that they use the free Lite data file.
# Each must finish, show the properties only the Enterprise data file has
# as needing it, and give the link to ask for a copy.

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_pipeline_core.logger import Logger

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise import csv_profile_metadata
from fiftyone_devicedetection_examples.onpremise import datafileupdate_console
from fiftyone_devicedetection_examples.onpremise import gettingstarted_console
from fiftyone_devicedetection_examples.onpremise import match_metrics
from fiftyone_devicedetection_examples.onpremise import metadata_console
from fiftyone_devicedetection_examples.onpremise import offlineprocessing
from fiftyone_devicedetection_examples.onpremise import profile_metadata_console
from fiftyone_devicedetection_shared.example_constants import EVIDENCE_FILE_NAME
from fiftyone_devicedetection_shared.example_constants import LITE_DATAFILE_NAME

# The settings the examples read, which a fresh clone does not have.
SETTINGS = ["license_key"]

# The evidence records the offline processing test reads. The example's own
# file has 20,000, which take minutes.
OFFLINE_RECORDS = 20


def run_without_settings(main, argv=None):
    """Runs an example's main with the settings taken out of the
    environment, and returns what it printed."""
    printed = io.StringIO()
    with mock.patch.dict(os.environ), redirect_stdout(printed):
        for name in SETTINGS:
            os.environ.pop(name, None)
        main(argv or [])
    return printed.getvalue()


def first_records(path, count):
    """The first records of a YAML evidence file."""
    lines = []
    with open(path, encoding="utf-8") as evidence:
        for line in evidence:
            if line.rstrip() == "---":
                count -= 1
                if count < 0:
                    break
            lines.append(line)
    return io.StringIO("".join(lines))


class ExamplesWithoutSettingsTests(unittest.TestCase):

    def test_gettingstarted_console(self):
        printed = run_without_settings(gettingstarted_console.main)
        self.assertIn(
            "Hardware Vendor: " + ExampleUtils.NEEDS_ENTERPRISE, printed)
        self.assertIn(
            ExampleUtils.get_enterprise_note(gettingstarted_console.CONTACT_US),
            printed)

    def test_match_metrics(self):
        printed = run_without_settings(match_metrics.main)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(match_metrics.CONTACT_US),
            printed)

    def test_metadata_console(self):
        printed = run_without_settings(metadata_console.main)
        self.assertIn(
            ExampleUtils.get_enterprise_offer(metadata_console.CONTACT_US),
            printed)

    def test_offline_processing(self):
        output = io.StringIO()
        lacks_properties = offlineprocessing.OfflineProcessing().run(
            ExampleUtils.find_file(LITE_DATAFILE_NAME),
            first_records(
                ExampleUtils.find_file(EVIDENCE_FILE_NAME), OFFLINE_RECORDS),
            Logger(min_level="error"),
            output)
        self.assertTrue(lacks_properties)
        self.assertIn(
            "device.hardwarevendor: " + ExampleUtils.NEEDS_ENTERPRISE,
            output.getvalue())
        self.assertIn(
            "# " + ExampleUtils.get_enterprise_note(
                offlineprocessing.CONTACT_US),
            output.getvalue())

    def test_datafileupdate_console(self):
        printed = run_without_settings(datafileupdate_console.main)
        self.assertIn("The data file in use is the 'Lite' file", printed)
        self.assertIn(datafileupdate_console.CONTACT_US, printed)

    # The two examples below need files that are not free, so in a fresh
    # clone the search for them finds nothing, which the tests stand in for.

    def test_csv_profile_metadata(self):
        with mock.patch.object(ExampleUtils, "find_file", return_value=None):
            printed = run_without_settings(csv_profile_metadata.main)
        self.assertIn(csv_profile_metadata.CSV_FILE_NAME, printed)
        self.assertIn(csv_profile_metadata.CONTACT_US, printed)

    def test_profile_metadata_console(self):
        with mock.patch.object(ExampleUtils, "find_file", return_value=None):
            printed = run_without_settings(profile_metadata_console.main)
        self.assertIn("only the Enterprise data file has", printed)
        self.assertIn(profile_metadata_console.CONTACT_US, printed)


if __name__ == "__main__":
    unittest.main()

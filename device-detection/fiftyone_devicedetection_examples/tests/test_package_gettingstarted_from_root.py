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
The getting started example in the fiftyone_devicedetection package, run
from the repository's root folder, finds the free Lite data file, says that
the hardware vendor needs the Enterprise data file, and gives the link to
ask for a copy.
"""

import io
import os
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils

ROOT = Path(__file__).resolve().parents[3]

EXAMPLE = (ROOT / "device-detection" / "fiftyone_devicedetection"
           / "examples" / "gettingstarted.py")

# The tag of the example's own link to ask for the Enterprise data file.
CONTACT_US_TAG = (
    "utm_content=fiftyone_devicedetection-examples-gettingstarted.py"
    "&utm_term=enterprise-data-file")


class PackageGettingStartedFromRootTests(unittest.TestCase):

    def test_runs_from_the_repository_root(self):
        printed = io.StringIO()
        folder = os.getcwd()
        os.chdir(ROOT)
        try:
            # The free file is the one under test, so a data file named in
            # the environment, as CI names the Enterprise file, is set
            # aside. The builder shares usage, so nothing is sent from a
            # test.
            with mock.patch.dict(os.environ):
                for name in (ExampleUtils.DD_PATH_ENV_VAR,
                             ExampleUtils.DATA_FILE_ENV_VAR):
                    os.environ.pop(name, None)
                with mock.patch("requests.post"), redirect_stdout(printed):
                    runpy.run_path(str(EXAMPLE), run_name="__main__")
        finally:
            os.chdir(folder)
        said = printed.getvalue()
        self.assertIn(
            "Who made the device? \n" + ExampleUtils.NEEDS_ENTERPRISE, said)
        self.assertIn(CONTACT_US_TAG, said)

    def test_reads_the_data_file_from_the_environment(self):
        # A data file named in _51DEGREES_DD_PATH that is not there makes
        # the example stop naming it, which shows the variable was read.
        missing = str(
            ROOT / "no-such-folder" / "named-by-the-environment.hash")
        folder = os.getcwd()
        os.chdir(ROOT)
        try:
            with mock.patch.dict(os.environ, {"_51DEGREES_DD_PATH": missing}):
                with mock.patch("requests.post"):
                    with redirect_stdout(io.StringIO()):
                        with self.assertRaises(Exception) as caught:
                            runpy.run_path(
                                str(EXAMPLE), run_name="__main__")
        finally:
            os.chdir(folder)
        self.assertIn(missing, str(caught.exception))


if __name__ == "__main__":
    unittest.main()

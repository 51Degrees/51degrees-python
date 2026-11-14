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
The getting started example in the fiftyone_ipintelligence package, run
from the repository's root folder, finds the free Lite data file, says that
the country needs the Enterprise data file, and gives the link to ask for a
copy.
"""

import io
import os
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils

ROOT = Path(__file__).resolve().parents[3]

EXAMPLE = (ROOT / "ip-intelligence" / "fiftyone_ipintelligence" / "examples"
           / "gettingstarted.py")

# The tag of the example's own link to ask for the Enterprise data file.
CONTACT_US_TAG = (
    "utm_content=fiftyone_ipintelligence-examples-gettingstarted.py"
    "&utm_term=enterprise-data-file")


class PackageGettingStartedFromRootTests(unittest.TestCase):

    def test_runs_from_the_repository_root(self):
        printed = io.StringIO()
        folder = os.getcwd()
        os.chdir(ROOT)
        try:
            with redirect_stdout(printed):
                runpy.run_path(str(EXAMPLE), run_name="__main__")
        finally:
            os.chdir(folder)
        said = printed.getvalue()
        self.assertIn(
            "Which country is IP address 185.28.167.78 in? \n"
            + ExampleUtils.NEEDS_ENTERPRISE,
            said)
        self.assertIn(CONTACT_US_TAG, said)


if __name__ == "__main__":
    unittest.main()

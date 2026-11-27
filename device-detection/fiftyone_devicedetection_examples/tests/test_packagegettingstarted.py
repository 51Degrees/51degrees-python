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

"""!
Runs the getting started example of the fiftyone_devicedetection package,
fiftyone_devicedetection/examples/gettingstarted.py, as it is. It opens the
free Lite data file by a path relative to the working directory, which leads
to the cxx submodule from the package's own folder, so it is run from there.

The pipeline builder it uses shares usage, and usage sharing sends what is
queued when the pipeline closes, so requests.post is replaced while it runs
and nothing is sent.
"""

import io
import os
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

# The fiftyone_devicedetection package's folder in this checkout.
PACKAGE = Path(__file__).resolve().parents[2] / "fiftyone_devicedetection"
EXAMPLE = PACKAGE / "examples" / "gettingstarted.py"

# The example prints this before each User-Agent it asks about, and the
# answer on the next line.
QUESTION = "Is User-Agent "


class PackageGettingStartedTests(unittest.TestCase):

    def test_runs_from_the_package_folder(self):
        printed = io.StringIO()
        working = os.getcwd()
        os.chdir(PACKAGE)
        try:
            with mock.patch(
                    "requests.post",
                    return_value=mock.Mock(status_code=200, text="")), \
                    redirect_stdout(printed):
                runpy.run_path(str(EXAMPLE), run_name="gettingstarted")
        finally:
            os.chdir(working)

        output = printed.getvalue()
        lines = output.splitlines()
        answers = [lines[index + 1] for index, line in enumerate(lines)
                   if line.startswith(QUESTION) and index + 1 < len(lines)]
        # A desktop browser first, then an iPhone.
        self.assertEqual(["False", "True"], answers, output)


if __name__ == "__main__":
    unittest.main()

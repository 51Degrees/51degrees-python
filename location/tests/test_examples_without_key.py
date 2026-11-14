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
Runs each cloud example as it runs from a fresh clone, with no resource key
set. Each must end without an error and give a tagged link to the page
where a key is created.
"""

import io
import os
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "cloud"

# Every name a key can be read from, which a fresh clone does not set.
KEY_SETTINGS = ["_51DEGREES_RESOURCE_KEY", "resource_key", "RESOURCE_KEY"]

# A link to the page where a resource key is created, with the campaign
# tags every example's links carry.
CONFIGURE_LINK = (
    r"https://51degrees\.com/configure[^\s?]*\?utm_source=code"
    r"&utm_medium=example&utm_campaign=51degrees-python&utm_content=")


def run_without_key(example):
    """Runs an example file as a script with no key in the environment, and
    returns what it printed."""
    printed = io.StringIO()
    with mock.patch.dict(os.environ), redirect_stdout(printed):
        for name in KEY_SETTINGS:
            os.environ.pop(name, None)
        runpy.run_path(str(EXAMPLES / example), run_name="__main__")
    return printed.getvalue()


class LocationExamplesWithoutKeyTests(unittest.TestCase):

    def test_cloud_getting_started(self):
        self.assertRegex(run_without_key("gettingstarted.py"), CONFIGURE_LINK)

    def test_cloud_web(self):
        self.assertRegex(run_without_key("web.py"), CONFIGURE_LINK)


if __name__ == "__main__":
    unittest.main()

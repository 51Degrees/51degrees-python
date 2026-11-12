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

"""Checks that the tests still read the data file path under the name its
environment variable had before, when the new name is not set.
"""

import contextlib
import io
import os
import unittest
from unittest import mock

from .constants import TestConstants

NEW_NAME = "_51DEGREES_IPI_PATH"
OLD_NAME = "IPINTELLIGENCEDATAFILE"


class OldNameTests(unittest.TestCase):

    def setUp(self):
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(NEW_NAME, None)
        os.environ.pop(OLD_NAME, None)

    def path(self):
        with contextlib.redirect_stderr(io.StringIO()):
            return TestConstants.get_data_file_path()

    def test_data_file_path_is_read_from_the_old_name(self):
        os.environ[OLD_NAME] = "old.ipi"
        self.assertEqual("old.ipi", self.path())

    def test_new_name_wins(self):
        os.environ[NEW_NAME] = "new.ipi"
        os.environ[OLD_NAME] = "old.ipi"
        self.assertEqual("new.ipi", self.path())

    def test_neither_name_gives_the_lite_file(self):
        self.assertTrue(self.path().endswith("51Degrees-LiteIpiV41.ipi"))


if __name__ == "__main__":
    unittest.main()

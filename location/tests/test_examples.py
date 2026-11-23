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

import os
import sys
import unittest
from pathlib import Path

from unittest import mock

from .live_cloud import (
    RESOURCE_KEY_VARIABLE, find_resource_key, no_resource_key)


class LocationExampleTests(unittest.TestCase):
    def test_cloud_getting_started(self):
        resource_key = find_resource_key()
        if not resource_key:
            self.skipTest(no_resource_key(
                "the location product",
                "the country at a latitude and longitude"))
        # this is required to import the example code,
        # since pytest sets sys.path to the test directory
        sys.path.append(str(Path(__file__).parent.parent.absolute() / "examples"))
        # The example reads its key when it is imported.
        with mock.patch.dict(
                os.environ, {RESOURCE_KEY_VARIABLE: resource_key}):
            import cloud.gettingstarted

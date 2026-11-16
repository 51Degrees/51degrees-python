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

import unittest
import warnings

from fiftyone_pipeline_engines import datafile_update_service
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService


# fiftyone_pipeline_engines 4.5.43 published REFRESH_TRIES at module level
# in datafile_update_service, with this value.
PUBLISHED_REFRESH_TRIES = 1


class RefreshTriesNameTests(unittest.TestCase):

    # Code written against 4.5 that imports the module level name still
    # imports it, and reads the value 4.5 gave it.
    def testTheModuleLevelNameImportsWithItsPublishedValue(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from fiftyone_pipeline_engines.datafile_update_service \
                import REFRESH_TRIES
        self.assertEqual(PUBLISHED_REFRESH_TRIES, REFRESH_TRIES)

    # Nothing in the package reads the module level name now, so a read of
    # it warns that it is deprecated and names what to read instead.
    def testReadingTheModuleLevelNameWarnsThatItIsDeprecated(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = datafile_update_service.REFRESH_TRIES
        self.assertEqual(PUBLISHED_REFRESH_TRIES, value)
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertEqual(1, len(deprecations))
        self.assertIn("REFRESH_TRIES", str(deprecations[0].message))
        self.assertIn(
            "DataFileUpdateService.REFRESH_TRIES",
            str(deprecations[0].message))
        self.assertEqual(__file__, deprecations[0].filename)

    # The tries a refresh makes are still the service's own, which the
    # module level name does not change.
    def testTheServiceKeepsItsOwnTries(self):
        self.assertEqual(10, DataFileUpdateService.REFRESH_TRIES)

    # A name the module never had is still an AttributeError.
    def testAnUnknownNameIsStillAnAttributeError(self):
        with self.assertRaises(AttributeError):
            datafile_update_service.NOT_A_NAME
        with self.assertRaises(ImportError):
            from fiftyone_pipeline_engines.datafile_update_service \
                import NOT_A_NAME  # noqa: F401


if __name__ == "__main__":
    unittest.main()

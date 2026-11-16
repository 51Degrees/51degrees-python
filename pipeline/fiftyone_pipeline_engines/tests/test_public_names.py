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
import unittest
import warnings

from fiftyone_pipeline_engines import datafile_update_service
from fiftyone_pipeline_engines.datafile_update_service import \
    DataFileUpdateService

# What the deprecation says, so a reader of a warning is sent to the name
# that holds the tries the service makes.
NEW_NAME = "DataFileUpdateService.REFRESH_TRIES"

# The old name, as the deprecation gives it.
OLD_NAME = ("fiftyone_pipeline_engines.datafile_update_service."
            "REFRESH_TRIES")


def same_file(first, second):
    """Whether two paths name the same file."""
    return (os.path.normcase(os.path.realpath(first)) ==
            os.path.normcase(os.path.realpath(second)))


def deprecations(caught):
    """The recorded warnings about the old name, so an unrelated warning
    from elsewhere does not count."""
    return [w for w in caught if OLD_NAME in str(w.message)]


class DeprecatedRefreshTriesTests(unittest.TestCase):

    """The module level REFRESH_TRIES this module published. The tries the
    service makes are DataFileUpdateService.REFRESH_TRIES, and a release
    removes no public name, so the old name still reads with the value it
    was given and a DeprecationWarning that names the new one."""

    def assert_one_deprecation(self, caught):
        """One DeprecationWarning was recorded, naming both the old name
        and the new one, and reported against the line in this file that
        read the name."""
        found = deprecations(caught)
        self.assertEqual(1, len(found), [str(w.message) for w in caught])
        warning = found[0]
        self.assertIs(DeprecationWarning, warning.category)
        self.assertIn(NEW_NAME, str(warning.message))
        self.assertTrue(same_file(__file__, warning.filename),
                        warning.filename)

    def test_a_from_import_warns_and_keeps_its_value(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from fiftyone_pipeline_engines.datafile_update_service import (
                REFRESH_TRIES as tries)
        self.assertEqual(1, tries)
        self.assert_one_deprecation(caught)

    def test_reading_it_from_the_module_warns_and_keeps_its_value(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tries = datafile_update_service.REFRESH_TRIES
        self.assertEqual(1, tries)
        self.assert_one_deprecation(caught)

    def test_the_module_does_not_hold_the_name(self):
        # Only __getattr__ gives it, so dir(), vars() and the tools that
        # list a module's names do not offer it, and the package itself
        # never reads it that way.
        self.assertNotIn("REFRESH_TRIES", vars(datafile_update_service))
        self.assertNotIn("REFRESH_TRIES", dir(datafile_update_service))

    def test_the_service_holds_the_tries_it_makes(self):
        self.assertIsInstance(DataFileUpdateService.REFRESH_TRIES, int)
        self.assertGreater(DataFileUpdateService.REFRESH_TRIES, 0)

    def test_a_name_the_module_does_not_hold_is_missing(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with self.assertRaises(AttributeError) as raised:
                datafile_update_service.NO_SUCH_NAME
        self.assertIn("NO_SUCH_NAME", str(raised.exception))
        self.assertEqual([], [str(w.message) for w in deprecations(caught)])


if __name__ == "__main__":
    unittest.main()

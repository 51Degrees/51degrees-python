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
AspectDataDictionary finds a value by its key in any letters, as Property
names are compared without regard to case.
"""

import unittest

from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary

from .test_engines import ExampleAspectEngine


class AspectDataDictionaryTests(unittest.TestCase):

    def test_get_internal_finds_a_key_in_any_letters(self):

        data = AspectDataDictionary(ExampleAspectEngine(), {"IsMobile": True})

        for key in ["IsMobile", "ISMOBILE", "ismobile"]:
            with self.subTest(key=key):
                self.assertTrue(data.get_internal(key))

    def test_get_finds_a_property_in_any_letters(self):

        data = AspectDataDictionary(ExampleAspectEngine(), {"integer": 5})

        for key in ["Integer", "INTEGER", "integer"]:
            with self.subTest(key=key):
                self.assertEqual(data.get(key), 5)


if __name__ == "__main__":
    unittest.main()

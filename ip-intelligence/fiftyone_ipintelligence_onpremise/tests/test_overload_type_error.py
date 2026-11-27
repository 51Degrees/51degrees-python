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

"""A call to the engine's overloaded constructor with arguments that match no
overload raises a TypeError that names the constructor, and does not crash
or build an engine. No data file is read."""

import unittest

from fiftyone_ipintelligence_onpremise.IpIntelligenceEngineModule import EngineIpiSwig


class TestOverloadTypeError(unittest.TestCase):

    def test_wrong_argument_types_raise_type_error(self):
        with self.assertRaises(TypeError) as raised:
            EngineIpiSwig(1, 2, 3)
        self.assertIn("new_EngineIpiSwig", str(raised.exception))

    def test_wrong_number_of_arguments_raises_type_error(self):
        with self.assertRaises(TypeError) as raised:
            EngineIpiSwig("file")
        self.assertIn("new_EngineIpiSwig", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

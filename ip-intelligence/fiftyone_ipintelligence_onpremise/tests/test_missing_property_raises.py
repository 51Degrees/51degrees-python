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

"""A property the engine lists, in a data file tier that holds it, raises
when the data has no value for it, as every missing property does."""

import unittest
from types import SimpleNamespace

from fiftyone_ipintelligence_onpremise.swig_data import \
    OnPremiseMissingPropertyService


class StandInEngine:
    """An engine whose data file is Lite, listing one property that the
    Lite file holds."""

    datakey = "ip"
    properties = {"registeredname": {"datafiles": ["Lite", "Enterprise"]}}
    engine = SimpleNamespace(getProduct=lambda: "Lite")


class MissingPropertyRaisesTests(unittest.TestCase):

    def test_a_listed_property_of_this_tier_raises(self):
        with self.assertRaises(Exception) as raised:
            OnPremiseMissingPropertyService().check(
                "registeredname", StandInEngine())

        self.assertEqual(
            "Property 'registeredname' not found in data for element 'ip'. "
            "This is because the property has been excluded when "
            "configuring the engine.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

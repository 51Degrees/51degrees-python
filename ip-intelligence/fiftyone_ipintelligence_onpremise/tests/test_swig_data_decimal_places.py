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
IP Intelligence Latitude and Longitude are given to 3 decimal places, as the
value types page of the specification says.
"""

import math
import unittest

from fiftyone_ipintelligence_onpremise import swig_data
from fiftyone_ipintelligence_onpremise.swig_data import SwigData


class Weighted:

    def __init__(self, value, weight):
        self.value = value
        self.weight = weight

    def getValue(self):
        return self.value

    def getWeight(self):
        return self.weight


class WeightedList:

    def __init__(self, items):
        self.items = items

    def hasValue(self):
        return True

    def getValue(self):
        return self.items


class Single:

    def __init__(self, value):
        self.value = value

    def hasValue(self):
        return True

    def getValue(self):
        return self.value


class FakeResults:

    def getValuesAsWeightedDoubleList(self, name):
        return WeightedList([Weighted(18.542741775512695, 65535),
                             Weighted(73.91278076171875, 100)])

    def getValueAsDouble(self, name):
        return Single(18.542741775512695)


class FakeElement:
    datakey = "ip"

    def __init__(self, type_name, name):
        self.properties = {name.lower(): {"name": name, "type": type_name}}


def read(type_name, name):
    data = SwigData(FakeElement(type_name, name), FakeResults())
    return data.get_internal(name.lower()).value()


class DecimalPlacesTests(unittest.TestCase):

    def test_weighted_latitude_and_longitude_have_three_places(self):
        for type_name in ("weighteddouble", "weightedsingle"):
            for name in ("Latitude", "Longitude"):
                values = [item["value"] for item in read(type_name, name)]
                self.assertEqual([18.543, 73.913], values, (type_name, name))

    def test_weights_are_unchanged(self):
        weights = [item["weighting"] for item in read("weighteddouble", "Latitude")]
        self.assertEqual([65535, 100], weights)

    def test_single_latitude_has_three_places(self):
        for type_name in ("double", "single"):
            self.assertEqual(18.543, read(type_name, "Latitude"))

    def test_other_numbers_are_not_rounded(self):
        values = [item["value"] for item in read("weighteddouble", "Accuracy")]
        self.assertEqual([18.542741775512695, 73.91278076171875], values)

    def test_the_unused_sixteen_place_setting_is_gone(self):
        self.assertFalse(hasattr(swig_data, "WKT_DECIMAL_PLACES"))

    def test_a_half_rounds_away_from_zero(self):
        for value, expected in ((0.0625, 0.063),
                                (-0.0625, -0.063),
                                (51.3125, 51.313)):
            self.assertEqual(expected, SwigData.round_coordinate(value), value)

    def test_a_value_that_rounds_to_zero_from_below_has_no_sign(self):
        for value in (-0.0004, -0.0):
            rounded = SwigData.round_coordinate(value)
            self.assertEqual(0.0, rounded, value)
            self.assertFalse(math.copysign(1.0, rounded) < 0,
                             f"{value} was given as minus zero")

    def test_a_value_that_is_not_finite_is_kept(self):
        infinity = float("inf")
        self.assertEqual(infinity, SwigData.round_coordinate(infinity))
        self.assertEqual(-infinity, SwigData.round_coordinate(-infinity))
        self.assertTrue(math.isnan(SwigData.round_coordinate(float("nan"))))


if __name__ == "__main__":
    unittest.main()

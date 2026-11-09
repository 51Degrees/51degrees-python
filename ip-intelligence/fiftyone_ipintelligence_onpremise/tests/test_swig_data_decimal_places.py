
"""
IP Intelligence Latitude and Longitude are given to 3 decimal places, as the
value types page of the specification says.
"""

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


if __name__ == "__main__":
    unittest.main()

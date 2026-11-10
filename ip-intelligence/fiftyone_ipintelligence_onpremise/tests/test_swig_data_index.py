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

"""Element Data reads each property by its index in the list of names the
engine was built with, through the engine's table, so the same index names
the same property after a reload."""

import unittest

from fiftyone_ipintelligence_onpremise.swig_data import SwigData


class Value:

    def __init__(self, value):
        self.value = value

    def hasValue(self):
        return True

    def getValue(self):
        return self.value


class RecordingResults:
    """Stands in for the native results and records what each read asks for."""

    def __init__(self):
        self.asked = []

    def read(self, target):
        self.asked.append(target)
        return Value(True)

    getValueAsBool = read
    getValueAsInteger = read


class FakeElement:
    datakey = "ip"
    properties = {
        "isproxy": {"name": "IsProxy", "type": "bool"},
        "accuracyradius": {"name": "AccuracyRadius", "type": "int"},
        "notbuilt": {"name": "NotBuilt", "type": "int"}}
    # The build-time names were AccuracyRadius then IsProxy.
    property_indexes = {"accuracyradius": 0, "isproxy": 1}


class SwigDataIndexTests(unittest.TestCase):

    def test_each_read_goes_by_the_build_time_index(self):
        results = RecordingResults()
        data = SwigData(FakeElement(), results)
        self.assertTrue(data.get("IsProxy").value())
        data.get("accuracyradius")
        self.assertEqual([1, 0], results.asked)

    def test_a_name_outside_the_table_is_read_by_name(self):
        results = RecordingResults()
        SwigData(FakeElement(), results).get("notbuilt")
        self.assertEqual(["NotBuilt"], results.asked)


if __name__ == "__main__":
    unittest.main()

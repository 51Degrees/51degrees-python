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

"""!
These tests run against fixed cloud responses, so they need no network
connection and no resource key. They cover the case that used to stop the
TAC and native model examples with an AttributeError, which is a resource
key that returns the hardware profiles but is not entitled to the hardware
properties themselves.
"""

import json
import unittest

from fiftyone_devicedetection_cloud.hardwareprofile_cloud import HardwareProfileCloud

# A response of the shape the cloud service returns for a TAC lookup when
# the resource key has the hardware aspect but is not entitled to the
# hardware properties. The values are null at the aspect level and each one
# is paired with a reason. The profiles carry only the properties the key is
# entitled to.
NOT_ENTITLED_RESPONSE = json.dumps({
    "hardware": {
        "profiles": [
            {"devicetype": "SmartPhone", "ismobile": True}
        ],
        "hardwarevendor": None,
        "hardwarevendornullreason":
            "HardwareVendor is a paid feature. You need a licence key to "
            "retrieve data.",
        "hardwarename": None,
        "hardwarenamenullreason":
            "HardwareName is a paid feature. You need a licence key to "
            "retrieve data.",
        "hardwaremodel": None,
        "hardwaremodelnullreason":
            "HardwareModel is a paid feature. You need a licence key to "
            "retrieve data."
    }
})

# A response from a fully entitled resource key.
ENTITLED_RESPONSE = json.dumps({
    "hardware": {
        "profiles": [
            {
                "hardwarevendor": "Apple",
                "hardwarename": ["iPhone 6"],
                "hardwaremodel": "A1586"
            }
        ]
    }
})

# A response where the hardware aspect is absent altogether, which is what a
# resource key without the hardware aspect returns.
NO_HARDWARE_RESPONSE = json.dumps({"device": {"ismobile": True}})


class _FakeCloudElementData:
    """!
    Stands in for the element data the cloud request engine publishes.
    """

    def __init__(self, response):
        self._response = response

    def get(self, key):
        return self._response


class _FakeFlowData:
    """!
    Stands in for a FlowData carrying a fixed cloud response, so the engine
    can be tested with no network connection and no resource key.
    """

    def __init__(self, response):
        self._response = response
        self.element_data = None

    def get(self, key):
        return _FakeCloudElementData(self._response)

    def set_element_data(self, data):
        self.element_data = data


def _process(response):
    """!
    Run a fixed cloud response through the hardware profile engine and
    return the resulting element data.
    """

    engine = HardwareProfileCloud()
    flowdata = _FakeFlowData(response)

    engine.process_internal(flowdata)

    return flowdata.element_data


class HardwareProfileCloudTests(unittest.TestCase):

    def test_null_reason_is_carried_into_each_profile(self):
        hardware = _process(NOT_ENTITLED_RESPONSE)
        profiles = hardware.get("profiles")

        self.assertEqual(1, len(profiles))

        profile = profiles[0]

        for name in ["hardwarevendor", "hardwarename", "hardwaremodel"]:
            self.assertIn(
                name, profile,
                f"'{name}' should be present on the profile so the reason "
                "it has no value can be reported")
            self.assertFalse(profile[name].has_value())
            self.assertIn("paid feature", profile[name].no_value_message())

    def test_null_reason_is_reported_by_the_example_helper(self):
        # The example helper lives in the examples package, which is not a
        # dependency of this one, so the same formatting is asserted here
        # against the values the engine produced.
        hardware = _process(NOT_ENTITLED_RESPONSE)
        profile = hardware.get("profiles")[0]
        value = profile["hardwarevendor"]

        self.assertEqual(
            "HardwareVendor is a paid feature. You need a licence key to "
            "retrieve data.",
            value.no_value_message())

    def test_entitled_values_are_reported_as_values(self):
        hardware = _process(ENTITLED_RESPONSE)
        profile = hardware.get("profiles")[0]

        self.assertTrue(profile["hardwarevendor"].has_value())
        self.assertEqual("Apple", profile["hardwarevendor"].value())
        self.assertEqual(["iPhone 6"], profile["hardwarename"].value())
        self.assertEqual("A1586", profile["hardwaremodel"].value())

    def test_absent_hardware_aspect_gives_no_profiles_rather_than_an_error(self):
        hardware = _process(NO_HARDWARE_RESPONSE)

        self.assertEqual([], hardware.get("profiles"))

    def test_aspect_level_values_are_exposed_alongside_the_profiles(self):
        # A caller with no matching profiles can still read the reason.
        hardware = _process(NOT_ENTITLED_RESPONSE)

        self.assertIn("paid feature",
                      hardware.get("hardwarevendor").no_value_message())


if __name__ == "__main__":
    unittest.main()

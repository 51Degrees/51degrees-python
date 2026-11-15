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
connection and no resource key. They cover a resource key that returns the
hardware profiles but is not entitled to the hardware properties themselves,
and how a profile is read, both as Aspect Data in the way the device data is
read and as a dict.
"""

import copy
import json
import pickle
import unittest

from fiftyone_devicedetection_cloud.hardwareprofile_cloud import HardwareProfileCloud
from fiftyone_pipeline_cloudrequestengine.clouddata import CloudData
from fiftyone_pipeline_engines.aspectdata import AspectData

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


class _KeyedFlowData:
    """!
    Stands in for a FlowData holding a cloud response under each key given.
    Asking for any other key raises, as a FlowData does.
    """

    def __init__(self, responses):
        self._responses = responses
        self.element_data = None

    def get(self, key):
        if key not in self._responses:
            raise Exception("There is no element data for " + key)
        return _FakeCloudElementData(self._responses[key])

    def set_element_data(self, data):
        self.element_data = data


def _process(response):
    """!
    Run a fixed cloud response through the hardware profile engine and
    return the resulting element data.
    """

    return _process_flowdata(_FakeFlowData(response))


def _process_flowdata(flowdata):
    """!
    Run the hardware profile engine on a stand-in FlowData and return the
    resulting element data.
    """

    engine = HardwareProfileCloud()

    engine.process_internal(flowdata)

    return flowdata.element_data


def _first_profile(response):
    """!
    The first hardware profile the engine made from a fixed cloud response.
    """

    return _process(response).get("profiles")[0]


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

    def test_the_response_is_read_under_cloud_response(self):
        # The cloud request engine's data is read under cloud-response, the
        # key the specification gives, rather than the deprecated cloud.
        hardware = _process_flowdata(_KeyedFlowData({
            "cloud-response": ENTITLED_RESPONSE,
            "cloud": NO_HARDWARE_RESPONSE}))

        self.assertEqual(
            "Apple", hardware.get("profiles")[0]["hardwarevendor"].value())

    def test_the_old_key_is_read_when_there_is_no_cloud_response(self):
        # An older cloud request engine gives its data under cloud alone.
        hardware = _process_flowdata(_KeyedFlowData({
            "cloud": ENTITLED_RESPONSE}))

        self.assertEqual(
            "Apple", hardware.get("profiles")[0]["hardwarevendor"].value())


class HardwareProfileAspectDataTests(unittest.TestCase):
    """!
    A profile is read in the way the device data is read, because each
    device detection engine returns Aspect Data that is interface compatible
    with the others.
    """

    def test_a_profile_is_aspect_data(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertIsInstance(profile, AspectData)

    def test_properties_are_read_as_attributes(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertIs(profile["hardwarevendor"], profile.hardwarevendor)
        self.assertIs(profile["hardwarename"], profile.hardwarename)
        self.assertIs(profile["hardwaremodel"], profile.hardwaremodel)
        self.assertEqual("Apple", profile.hardwarevendor.value())

    def test_attributes_are_read_in_any_letter_case(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertIs(profile["hardwarevendor"], profile.HardwareVendor)
        self.assertIs(profile["hardwaremodel"], profile.HARDWAREMODEL)

    def test_a_property_with_no_value_is_read_as_an_attribute(self):
        profile = _first_profile(NOT_ENTITLED_RESPONSE)

        self.assertFalse(profile.hardwarevendor.has_value())
        self.assertIn("paid feature",
                      profile.hardwarevendor.no_value_message())

    def test_names_are_compared_ignoring_letter_case(self):
        profile = _first_profile(ENTITLED_RESPONSE)
        value = profile["hardwarevendor"]

        self.assertIs(value, profile["HardwareVendor"])
        self.assertIs(value, profile.get("HardwareVendor"))
        self.assertIs(value, profile.get_internal("HardwareVendor"))
        self.assertIn("HardwareVendor", profile)

    def test_a_name_that_is_not_a_property_gives_the_device_data_message(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        # The device data is CloudData, so CloudData for the same engine
        # gives the message the device data gives.
        with self.assertRaises(Exception) as expected:
            CloudData(HardwareProfileCloud(), {}).get("notaproperty")

        with self.assertRaises(AttributeError) as raised:
            profile.notaproperty

        self.assertEqual(str(expected.exception), str(raised.exception))

    def test_hasattr_and_getattr_with_a_default_work(self):
        profile = _first_profile(ENTITLED_RESPONSE)
        default = object()

        self.assertTrue(hasattr(profile, "hardwarevendor"))
        self.assertFalse(hasattr(profile, "notaproperty"))
        self.assertIs(profile["hardwarevendor"],
                      getattr(profile, "hardwarevendor", default))
        self.assertIs(default, getattr(profile, "notaproperty", default))

    def test_as_dictionary_gives_every_property(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertEqual(
            ["hardwaremodel", "hardwarename", "hardwarevendor"],
            sorted(profile.as_dictionary()))


class HardwareProfileDictTests(unittest.TestCase):
    """!
    A profile is also a dict of property name to AspectPropertyValue, and
    behaves as one.
    """

    def test_indexing_by_name(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertEqual("Apple", profile["hardwarevendor"].value())

        with self.assertRaises(KeyError) as raised:
            profile["notaproperty"]

        self.assertEqual(("notaproperty",), raised.exception.args)

    def test_get_with_a_default(self):
        profile = _first_profile(ENTITLED_RESPONSE)
        default = object()

        self.assertEqual("Apple", profile.get("hardwarevendor").value())
        self.assertIsNone(profile.get("notaproperty"))
        self.assertIs(default, profile.get("notaproperty", default))

    def test_in_iteration_len_keys_and_equality(self):
        profile = _first_profile(ENTITLED_RESPONSE)
        names = ["hardwaremodel", "hardwarename", "hardwarevendor"]

        self.assertIsInstance(profile, dict)
        self.assertIn("hardwarevendor", profile)
        self.assertNotIn("notaproperty", profile)
        self.assertEqual(names, sorted(profile))
        self.assertEqual(names, sorted(profile.keys()))
        self.assertEqual(3, len(profile))
        self.assertEqual({name: profile[name] for name in names}, profile)

    def test_copies_and_pickles(self):
        profile = _first_profile(ENTITLED_RESPONSE)

        self.assertIs(profile["hardwarevendor"],
                      copy.copy(profile)["hardwarevendor"])
        self.assertEqual(
            "Apple", copy.deepcopy(profile)["hardwarevendor"].value())
        self.assertEqual(
            "A1586",
            pickle.loads(pickle.dumps(profile))["hardwaremodel"].value())


if __name__ == "__main__":
    unittest.main()

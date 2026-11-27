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
Tests how the live tests read what the TAC and native model lookup examples
print, with made-up output, so they run without a key and catch a fault in
the reading before a live run with a good key would.
"""

import unittest

from .hardware_lookup_output import lookup_fault, vendor_and_model

# What ExampleUtils.get_human_readable gives for a property that is not in
# the results.
UNKNOWN_VENDOR = (
    "Unknown (the property 'hardwarevendor' is not in the results, so the "
    "current resource key does not include it)")
UNKNOWN_NAME = (
    "Unknown (the property 'hardwarename' is not in the results, so the "
    "current resource key does not include it)")
UNKNOWN_MODEL = (
    "Unknown (the property 'hardwaremodel' is not in the results, so the "
    "current resource key does not include it)")

TAC_HEADING = "Which devices are associated with the TAC '{}'?"
TACS = ("35925406", "86386802")

# The section every example ends with. Its links are indented as device
# lines are.
FIND_OUT_MORE = "\n".join([
    "=" * 79,
    "Find out more:",
    "\tDevice detection: https://example.com/device-detection",
])


def tac_output(*lines_for_each_tac):
    """What the TAC example prints, with the lines given for each TAC under
    its heading, followed by the Find out more section."""
    lines = ["This example shows the details of devices.", "-" * 40]
    for tac, under in zip(TACS, lines_for_each_tac):
        lines.append(TAC_HEADING.format(tac))
        lines.extend(under)
    return "\n".join(lines) + "\n" + FIND_OUT_MORE


class VendorAndModelTests(unittest.TestCase):

    def test_a_device_line_gives_its_vendor_and_model(self):
        self.assertEqual(
            ("Apple", "A1586"), vendor_and_model("\tApple iPhone 6 (A1586)"))

    def test_a_model_holding_parentheses_is_read_whole(self):
        self.assertEqual(
            ("Apple", "A1586 (Global)"),
            vendor_and_model("\tApple iPhone 6 (A1586 (Global))"))

    def test_an_unknown_model_is_read_with_its_reason(self):
        self.assertEqual(
            ("Apple", UNKNOWN_MODEL),
            vendor_and_model(f"\tApple iPhone 6 ({UNKNOWN_MODEL})"))

    def test_an_empty_model_is_read_as_empty(self):
        self.assertEqual(
            ("Apple", ""), vendor_and_model("\tApple iPhone 6 ()"))

    def test_the_no_devices_line_is_not_a_device(self):
        self.assertIsNone(
            vendor_and_model("\tNo devices are associated with this TAC."))

    def test_a_line_with_nothing_before_the_model_is_not_a_device(self):
        self.assertIsNone(vendor_and_model("\t(A1586)"))

    def test_a_line_with_unbalanced_parentheses_is_not_a_device(self):
        self.assertIsNone(vendor_and_model("\tApple iPhone 6 A1586)"))


class LookupFaultTests(unittest.TestCase):

    def assert_fault(self, expected, output):
        self.assertEqual(
            expected, lookup_fault(output, "TAC lookup", "TAC", TACS))

    def test_a_device_under_each_heading_is_no_fault(self):
        self.assert_fault(None, tac_output(
            ["\tApple iPhone 6 (A1586)"],
            ["\tCoolpad 5217 (5217)", "\tCoolpad 5200 (5200)"]))

    def test_a_model_holding_parentheses_counts(self):
        self.assert_fault(None, tac_output(
            ["\tApple iPhone 6 (A1586 (Global))"],
            ["\tCoolpad 5217 (5217)"]))

    def test_one_device_with_a_vendor_and_a_model_is_enough(self):
        self.assert_fault(None, tac_output(
            ["\tApple iPhone 6 (A1586)"],
            [f"\tCoolpad 5217 ({UNKNOWN_MODEL})", "\tCoolpad 5200 (5200)"]))

    def test_an_unknown_vendor_and_model_do_not_count(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'35925406'.",
            tac_output(
                [f"\t{UNKNOWN_VENDOR} {UNKNOWN_NAME} ({UNKNOWN_MODEL})"],
                ["\tCoolpad 5217 (5217)"]))

    def test_an_unknown_model_does_not_count(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'35925406'.",
            tac_output(
                [f"\tApple iPhone 6 ({UNKNOWN_MODEL})"],
                ["\tCoolpad 5217 (5217)"]))

    def test_an_empty_model_does_not_count(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'86386802'.",
            tac_output(
                ["\tApple iPhone 6 (A1586)"],
                ["\tCoolpad 5217 ()"]))

    def test_the_no_devices_line_does_not_count(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'86386802'.",
            tac_output(
                ["\tApple iPhone 6 (A1586)"],
                ["\tNo devices are associated with this TAC."]))

    def test_a_device_line_without_a_tab_does_not_count(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'35925406'.",
            tac_output(
                ["Apple iPhone 6 (A1586)"],
                ["\tCoolpad 5217 (5217)"]))

    def test_a_missing_heading_is_a_fault(self):
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'86386802'.",
            tac_output(["\tApple iPhone 6 (A1586)"]))

    def test_the_find_out_more_links_are_not_devices(self):
        # The last heading is followed straight by the section's links,
        # which are indented as device lines are.
        self.assert_fault(
            "No device with a vendor and a model was listed for the TAC "
            "'86386802'.",
            tac_output(["\tApple iPhone 6 (A1586)"], []))

    def test_a_key_without_the_lookup_is_named(self):
        output = (
            "The resource key does not include HardwarePlatform.Profiles, "
            "the hardware lookup this example needs, so no devices are "
            "listed.\n" + FIND_OUT_MORE)
        self.assertEqual(
            "The resource key in _51DEGREES_RESOURCE_KEY_BESPOKE does not "
            "include HardwarePlatform.Profiles, which the TAC lookup needs.",
            lookup_fault(output, "TAC lookup", "TAC", TACS))
        self.assertEqual(
            "The resource key in _51DEGREES_RESOURCE_KEY_BESPOKE does not "
            "include HardwarePlatform.Profiles, which the native model "
            "lookup needs.",
            lookup_fault(output, "native model lookup", "native model name",
                         ("SC-03L", "iPhone11,8")))


if __name__ == "__main__":
    unittest.main()

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
The reason an on-premise engine gives for a missing property, decided in
the order the properties specification sets out, with the message of the
missing properties table for that reason.
"""

import unittest

from fiftyone_pipeline_engines.missingproperty_service import \
    OnPremiseMissingPropertyService

# The pricing page the data file rows link to, with this repository's
# campaign parameters.
PRICING = "https://51degrees.com/pricing?utm_source=code&utm_medium=comment&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-src-fiftyone_pipeline_engines-missingproperty_service.py&utm_term=missing-property-pricing"


class StandInNativeEngine:
    """Stands in for the native engine, giving the data file's tier."""

    def __init__(self, tier):
        self.tier = tier

    def getProduct(self):
        return self.tier


class StandInEngine:
    """Stands in for an on-premise engine, with its property metadata keyed
    by lower-case name as the engines keep it."""

    def __init__(self, tier, properties):
        self.datakey = "device"
        self.engine = StandInNativeEngine(tier)
        self.properties = properties

    def get_properties(self):
        return self.properties


def message(name, engine):
    with unittest.TestCase().assertRaises(Exception) as raised:
        OnPremiseMissingPropertyService().check(name, engine)
    return str(raised.exception)


class OnPremiseReasonTests(unittest.TestCase):

    def test_a_property_of_other_tiers_needs_an_upgrade(self):
        engine = StandInEngine("Lite", {
            "screenpixelsheight": {"datafiles": ["Premium", "Enterprise"]}})
        self.assertEqual(
            "Property 'ScreenPixelsHeight' not found in data for element "
            "'device'. This is because your license or data file does not "
            "include this property. It is available with the "
            "Premium,Enterprise license/data for the StandInEngine. To "
            "upgrade, see " + PRICING + ".",
            message("ScreenPixelsHeight", engine))

    def test_a_property_with_no_tiers_known_needs_an_upgrade(self):
        engine = StandInEngine("Lite", {"screenpixelsheight": {
            "datafiles": []}})
        self.assertEqual(
            "Property 'screenpixelsheight' not found in data for element "
            "'device'. This is because your license or data file does not "
            "include this property. To see which licenses include it, see "
            + PRICING + ".",
            message("screenpixelsheight", engine))

    def test_a_property_of_this_tier_was_excluded(self):
        engine = StandInEngine("Enterprise", {
            "screenpixelsheight": {"datafiles": ["Premium", "Enterprise"]}})
        self.assertEqual(
            "Property 'screenpixelsheight' not found in data for element "
            "'device'. This is because the property has been excluded when "
            "configuring the engine.",
            message("screenpixelsheight", engine))

    def test_a_property_the_metadata_does_not_list_is_unknown(self):
        engine = StandInEngine("Enterprise", {
            "screenpixelsheight": {"datafiles": ["Enterprise"]}})
        self.assertEqual(
            "Property 'notthere' not found in data for element 'device'. "
            "The reason for this is unknown. Please check that the aspect "
            "and property name are correct.",
            message("notthere", engine))

    def test_names_are_compared_ignoring_case(self):
        engine = StandInEngine("Lite", {
            "screenpixelsheight": {"datafiles": ["Enterprise"]}})
        for name in ("screenpixelsheight", "SCREENPIXELSHEIGHT",
                     "ScreenPixelsHeight"):
            with self.subTest(name=name):
                self.assertIn(
                    "It is available with the Enterprise license/data",
                    message(name, engine))


if __name__ == "__main__":
    unittest.main()

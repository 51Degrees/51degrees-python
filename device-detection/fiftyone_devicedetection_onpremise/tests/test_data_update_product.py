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

"""The data file names the Distributor's product for the data file in use,
which the data file update service asks for when the license key holds
several products."""

import unittest
from types import SimpleNamespace

from fiftyone_devicedetection_onpremise.devicedetection_datafile import \
    DeviceDetectionDataFile


def data_file(flow_element):
    """A data file of the flow element, which reads no file."""
    return DeviceDetectionDataFile(
        flow_element=flow_element, identifier="HashV41",
        path="not-read.hash",
        update_url_params={"base_url": "https://example.com/update"})


def loaded(tier):
    """Stands in for an engine that has loaded a data file of the tier."""
    return SimpleNamespace(engine=SimpleNamespace(getProduct=lambda: tier))


class DataUpdateProductTests(unittest.TestCase):

    def test_the_product_is_named_from_the_tier_of_the_data_file(self):
        for tier, product in (
                ("TAC", "V4TAC"),
                ("Enterprise", "V4Enterprise"),
                ("V4TAC", "V4TAC")):
            with self.subTest(tier):
                self.assertEqual(
                    product,
                    data_file(loaded(tier)).get_data_update_product())

    def test_no_product_is_named_before_a_data_file_is_loaded(self):
        # The update on start-up runs before the engine is built, and a
        # closed engine holds none.
        for name, flow_element in (
                ("not built", SimpleNamespace()),
                ("closed", SimpleNamespace(engine=None)),
                ("no tier", loaded(""))):
            with self.subTest(name):
                self.assertIsNone(
                    data_file(flow_element).get_data_update_product())


def formatted(product):
    """The update URL the URL formatter writes for a data file that is
    configured with the product."""
    return DeviceDetectionDataFile(
        flow_element=SimpleNamespace(), identifier="HashV41",
        path="not-read.hash", data_update_use_url_formatter=True,
        update_url_params={
            "base_url": "https://example.com/update",
            "type": "HashV41",
            "license_keys": "ABCDEFGHIJKL",
            "product": product}).get_update_url()


# A product is named in the update URL only when one is configured. Every
# request is made to that URL, so with a product configured every request
# names it, the first included, and with none configured the first request
# has no Product parameter at all.
class ConfiguredProductTests(unittest.TestCase):

    def test_a_configured_product_is_named_in_the_update_url(self):
        self.assertEqual(
            "https://example.com/update?Type=HashV41&"
            "licenseKeys=ABCDEFGHIJKL&Product=V4TAC",
            formatted("V4TAC"))

    def test_no_product_is_named_when_none_is_configured(self):
        for name, product in (("none", None), ("empty", "")):
            with self.subTest(name):
                url = formatted(product)
                self.assertEqual(
                    "https://example.com/update?Type=HashV41&"
                    "licenseKeys=ABCDEFGHIJKL", url)
                self.assertNotIn("product", url.lower())


if __name__ == "__main__":
    unittest.main()

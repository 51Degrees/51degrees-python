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

"""Runs the custom flow element example,
examples/client_side_evidence_custom_flow_element.py, through Flask's test
client. The page works out a star sign from a date of birth in the query
string, and a hemisphere from a latitude cookie, and the JSON route answers
with both for the page's script."""

import importlib.util
import json
import unittest
from pathlib import Path

EXAMPLE = (Path(__file__).resolve().parents[1] / "examples" /
           "client_side_evidence_custom_flow_element.py")

# A date of birth in the form a date input submits, and its star sign.
DATE_OF_BIRTH = "1990-03-25"
STAR_SIGN = "aries"

# The cookie the example's JavaScript sets with the browser's latitude. The
# test client sends only the cookies it holds, and drops a Cookie header
# passed with a request, so each test sets the cookie on the client.
LATITUDE_COOKIE = "latitude"
SOUTHERN_LATITUDE = "-33.9"
NORTHERN_LATITUDE = "51.5"


def load_example():
    """Runs the example's file as a module and returns the module."""
    spec = importlib.util.spec_from_file_location(
        "client_side_evidence_example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClientSideEvidenceExampleTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.example = load_example()

    @classmethod
    def tearDownClass(cls):
        cls.example.myPipeline.close()
        super().tearDownClass()

    def setUp(self):
        self.client = self.example.app.test_client()

    def get_page(self, **options):
        response = self.client.get("/", **options)
        page = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code, page)
        return page

    def test_page_holds_the_form_and_the_script(self):
        page = self.get_page()

        self.assertIn("<h1>Starsign</h1>", page)
        self.assertIn("name='dateOfBirth'", page)
        # The script the JavaScript builder writes posts to the JSON route.
        self.assertIn("/json", page)
        self.assertIn("const loadHemisphere", page)
        self.assertNotIn("Your starsign is", page)

    def test_page_gives_the_star_sign_for_the_date_of_birth(self):
        page = self.get_page(query_string={"dateOfBirth": DATE_OF_BIRTH})

        self.assertIn(f"<p>Your starsign is {STAR_SIGN}</p>", page)

    def test_page_gives_the_hemisphere_for_the_latitude_cookie(self):
        self.client.set_cookie(LATITUDE_COOKIE, NORTHERN_LATITUDE)
        page = self.get_page()

        self.assertIn(
            "<p>Look at the Northern hemisphere stars tonight!</p>", page)

    def test_json_route_gives_both_for_the_page_script(self):
        self.client.set_cookie(LATITUDE_COOKIE, SOUTHERN_LATITUDE)
        response = self.client.post(
            "/json", data={"dateOfBirth": DATE_OF_BIRTH})
        text = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, text)
        self.assertEqual("application/json", response.headers["Content-Type"])
        astrology = json.loads(text)["astrology"]
        self.assertEqual(STAR_SIGN, astrology["starsign"])
        self.assertEqual("Southern", astrology["hemisphere"])
        self.assertIn("navigator.geolocation", astrology["getlatitude"])


if __name__ == "__main__":
    unittest.main()

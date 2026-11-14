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

"""Runs the cloud web example, examples/cloud/web.py, against the live cloud
service. Its page is requested through Flask's test client, and so is the
JSON the page's script asks for once it has the browser's position."""

import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from .live_cloud import answered_without, find_resource_key, no_resource_key

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "cloud" / "web.py"

NO_KEY = no_resource_key(
    "the location product",
    "the country at a latitude and longitude", several=True)

# The variable the example reads its resource key from.
RESOURCE_KEY_VARIABLE = "_51DEGREES_RESOURCE_KEY"

# What the page's script posts once the browser gives it a position, which
# is in Reading, in the United Kingdom.
POSITION = {
    "51D_Pos_latitude": "51.4578261",
    "51D_Pos_longitude": "-0.975922996290084",
}

# The Cache-Control of a client-side response whose processing failed.
AFTER_ERRORS = "private, no-cache"


def load_example(resource_key):
    """Runs the example's file as a module, with the resource key in its
    environment, and returns the module."""
    spec = importlib.util.spec_from_file_location(
        "location_cloud_web_example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, {RESOURCE_KEY_VARIABLE: resource_key}):
        spec.loader.exec_module(module)
    return module


class LocationWebExampleTests(unittest.TestCase):

    resource_key = find_resource_key()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.example = load_example(cls.resource_key) \
            if cls.resource_key else None

    @classmethod
    def tearDownClass(cls):
        if cls.example is not None:
            cls.example.pipeline.close()
        super().tearDownClass()

    def setUp(self):
        if not self.resource_key:
            self.fail(NO_KEY)
        self.client = self.example.app.test_client()

    def test_page_holds_the_script_that_asks_for_the_position(self):
        response = self.client.get("/")
        page = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, page)
        self.assertIn("<h1>Client side evidence</h1>", page)
        # The script posts to the example's JSON route.
        self.assertIn("/json", page)

    def test_json_route_gives_the_country_at_the_position(self):
        response = self.client.post("/json", data=POSITION)
        text = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, text)
        self.assertEqual("application/json", response.headers["Content-Type"])
        self.assertNotEqual(
            AFTER_ERRORS, response.headers.get("Cache-Control"),
            "Processing the request failed.")
        location = json.loads(text).get("location", {})
        self.assertTrue(
            location.get("country"),
            answered_without("a country", location.get("countrynullreason"),
                             "the location product"))


if __name__ == "__main__":
    unittest.main()

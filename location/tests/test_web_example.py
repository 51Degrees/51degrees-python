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
JSON the page's script asks for once it has the browser's position.

The cloud service's own location lookup sometimes takes too long, and then
answers without a country and with the reason "Timeout processing location
request". That passes on a later request, so the JSON is asked for again on
that reason alone, a few times, before the test fails."""

import importlib.util
import json
import os
import time
import unittest
from pathlib import Path
from unittest import mock

import pytest

from .live_cloud import (
    RESOURCE_KEY_VARIABLE, answered_without, find_resource_key,
    no_resource_key)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "cloud" / "web.py"

NO_KEY = no_resource_key(
    "the location product",
    "the country at a latitude and longitude", several=True)

# What the page's script posts once the browser gives it a position, which
# is in Reading, in the United Kingdom.
POSITION = {
    "51D_Pos_latitude": "51.4578261",
    "51D_Pos_longitude": "-0.975922996290084",
}

# The Cache-Control of a client-side response whose processing failed.
AFTER_ERRORS = "private, no-cache"

# The reason the cloud service gives when its location lookup took too long.
LOOKUP_TIMEOUT = "timeout processing location request"

# The requests made before a lookup that took too long counts as a failure.
ATTEMPTS = 3

# Seconds between requests whose lookup took too long.
PAUSE_SECONDS = 2


def post_position(client, sleep=time.sleep):
    """Posts the position to the example's JSON route, asking again while
    the cloud service's location lookup takes too long, and returns the last
    response, its text and its location section."""
    for attempt in range(ATTEMPTS):
        response = client.post("/json", data=POSITION)
        text = response.get_data(as_text=True)
        try:
            location = json.loads(text).get("location", {})
        except ValueError:
            return response, text, {}
        reason = (location.get("countrynullreason") or "").lower()
        if (location.get("country") or LOOKUP_TIMEOUT not in reason
                or attempt == ATTEMPTS - 1):
            return response, text, location
        sleep(PAUSE_SECONDS)


def country_failure(location):
    """What to fail with when the answer has no country. A lookup that took
    too long on every request is said so, and any other reason points at the
    key, as that is what a key without the location product gets."""
    reason = location.get("countrynullreason")
    if LOOKUP_TIMEOUT in (reason or "").lower():
        return (f"The cloud service's location lookup took too long on all "
                f"{ATTEMPTS} requests ({reason}).")
    return answered_without("a country", reason, "the location product")


def load_example(resource_key):
    """Runs the example's file as a module, with the resource key in its
    environment, and returns the module."""
    spec = importlib.util.spec_from_file_location(
        "location_cloud_web_example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, {RESOURCE_KEY_VARIABLE: resource_key}):
        spec.loader.exec_module(module)
    return module


@pytest.mark.live
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
            self.skipTest(NO_KEY)
        self.client = self.example.app.test_client()

    def test_page_holds_the_script_that_asks_for_the_position(self):
        response = self.client.get("/")
        page = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, page)
        self.assertIn("<h1>Client side evidence</h1>", page)
        # The script posts to the example's JSON route.
        self.assertIn("/json", page)

    def test_json_route_gives_the_country_at_the_position(self):
        response, text, location = post_position(self.client)

        self.assertEqual(200, response.status_code, text)
        self.assertEqual("application/json", response.headers["Content-Type"])
        self.assertNotEqual(
            AFTER_ERRORS, response.headers.get("Cache-Control"),
            "Processing the request failed.")
        self.assertTrue(location.get("country"), country_failure(location))


class StandInResponse:

    def __init__(self, location):
        self.text = json.dumps({"location": location})

    def get_data(self, as_text=False):
        return self.text


class StandInClient:
    """Answers each post with the next location section given."""

    def __init__(self, *locations):
        self.locations = list(locations)
        self.posts = 0

    def post(self, path, data=None):
        self.posts += 1
        return StandInResponse(self.locations.pop(0))


TIMED_OUT = {"country": None,
             "countrynullreason": "Timeout processing location request"}
NOT_CARRIED = {"country": None,
               "countrynullreason": "The key does not include location"}
ANSWERED = {"country": "United Kingdom"}


class PostPositionTests(unittest.TestCase):
    """The asking again, against a stand-in for the example, so these run
    with no resource key."""

    def setUp(self):
        self.pauses = []

    def post(self, client):
        return post_position(client, sleep=self.pauses.append)[2]

    def test_a_lookup_that_took_too_long_is_asked_again(self):
        client = StandInClient(TIMED_OUT, ANSWERED)

        self.assertEqual(ANSWERED, self.post(client))
        self.assertEqual(2, client.posts)
        self.assertEqual([PAUSE_SECONDS], self.pauses)

    def test_any_other_reason_is_not_asked_again(self):
        client = StandInClient(NOT_CARRIED, ANSWERED)

        self.assertEqual(NOT_CARRIED, self.post(client))
        self.assertEqual(1, client.posts)

    def test_a_lookup_that_took_too_long_each_time_is_said_so(self):
        message = country_failure(TIMED_OUT)

        self.assertIn("took too long", message)
        self.assertIn(str(ATTEMPTS), message)
        self.assertNotIn("key", message)

    def test_any_other_reason_points_at_the_key(self):
        self.assertEqual(
            answered_without("a country", NOT_CARRIED["countrynullreason"],
                             "the location product"),
            country_failure(NOT_CARRIED))

    def test_it_stops_after_the_attempts(self):
        client = StandInClient(*[TIMED_OUT] * (ATTEMPTS + 1))

        self.assertEqual(TIMED_OUT, self.post(client))
        self.assertEqual(ATTEMPTS, client.posts)
        self.assertEqual([PAUSE_SECONDS] * (ATTEMPTS - 1), self.pauses)


if __name__ == "__main__":
    unittest.main()

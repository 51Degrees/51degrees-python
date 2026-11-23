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
Runs the Human Confidence web example against a stand-in for the cloud
service, so each step is checked with known values and without a key. The
stand-in answers in the shapes the example reads, and keeps the requests it
was sent, so the tests see what the example passed on.
"""

import json
import re

import pytest
import requests

from fiftyone_pipeline_examples.cloud.humanconfidence_web import (
    app as example)
from fiftyone_pipeline_examples.example_utils import ExampleUtils

from helpers import key_carries

API = "https://cloud.example/api/v4/"
RESOURCE_KEY = "a-resource-key"
LICENCE_KEY = "a-licence-key"

DESKTOP_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Every name a setting of the example is read from.
SETTINGS = [
    ExampleUtils.RESOURCE_KEY_ENV_VAR,
    ExampleUtils.LICENSE_KEY_ENV_VAR,
    ExampleUtils.CLOUD_ENDPOINT_ENV_VAR,
    "_51DEGREES_EXAMPLE_HTTP_PORTS",
]

# A 51degrees.com link.
LINK = re.compile(r"https://51degrees\.com/\S+")

# The tags every link the example prints carries, up to the name of its
# file.
TAGS = (
    "?utm_source=code&utm_medium=example&utm_campaign=51degrees-python"
    "&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-"
    "fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=")


class StubResponse:

    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        return json.loads(self.text)


class StubCloud:
    """
    Answers as the cloud service does for a key carrying the named
    properties, and keeps the requests it was sent as method, address and
    form fields.
    """

    def __init__(self, properties):
        self.properties = properties
        self.requests = []
        # The sealed values already redeemed, as each redeems once.
        self.redeemed = set()
        # An answer to give in place of the usual one, by the end of the
        # address, as a StubResponse or an exception to raise.
        self.instead = {}

    def sent_to(self, ending):
        """The requests sent to the addresses with the ending."""
        return [sent for sent in self.requests if sent[1].endswith(ending)]

    def request(self, method, url, data=None, headers=None, timeout=None):
        data = dict(data or {})
        self.requests.append((method, url, data))
        assert url.startswith(API), url
        path = url[len(API):]

        for ending, answer in self.instead.items():
            if path.endswith(ending):
                if isinstance(answer, BaseException):
                    raise answer
                return answer

        if path.startswith("accessibleproperties"):
            return StubResponse({"Products": {"derived": {"Properties": [
                {"Name": name, "Type": "String"}
                for name in self.properties]}}})

        if path == "evidencekeys":
            return StubResponse([
                "header.user-agent", "header.sec-ch-ua", "query.client-ip"])

        if path == RESOURCE_KEY + ".json":
            return StubResponse({"derived": {
                "humanconfidence": "Medium",
                "humanconfidencesource": "Passive"}})

        if path == "hc/redeem":
            if data.get("value") in self.redeemed:
                return StubResponse({"result": "replayed"})
            self.redeemed.add(data.get("value"))
            return StubResponse({
                "humanConfidence": "High", "secondsSinceVerified": 2})

        return StubResponse("Not Found", 404)


@pytest.fixture
def cloud(monkeypatch):
    """Makes a stand-in for the cloud service answer every request."""

    def stand_in(properties=("HumanConfidence", "HumanConfidenceSource")):
        stub = StubCloud(properties)
        monkeypatch.setattr(requests, "request", stub.request)
        return stub

    return stand_in


def client_for(license_key=LICENCE_KEY):
    return example.create_app(RESOURCE_KEY, license_key, API).test_client()


# The page.

def test_page_carries_the_resource_key_and_the_cloud_address(cloud):
    cloud()
    client = client_for()
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Human Confidence demo" in html
    assert f'var RESOURCE = "{RESOURCE_KEY}";' in html
    assert f'var API = "{API}";' in html
    assert '<link rel="stylesheet" href="/css/examples-main.min.css">' in html
    assert client.get("/css/examples-main.min.css").status_code == 200


def test_page_is_never_kept_by_a_cache(cloud):
    cloud()
    assert client_for().get("/").headers["Cache-Control"] == "no-store"


def test_page_is_served_without_asking_the_cloud(cloud):
    stub = cloud()
    client_for().get("/")
    assert stub.requests == []


def test_licence_key_never_reaches_the_page(cloud):
    cloud()
    assert LICENCE_KEY not in client_for().get("/").get_data(as_text=True)


def test_page_ends_with_its_find_out_more_section(cloud):
    cloud()
    html = client_for().get("/").get_data(as_text=True)
    section = html.split("Find out more", 1)[1]
    links = LINK.findall(section)
    assert links
    for link in links:
        assert "utm_medium=example" in link
        assert "utm_term=find-out-more" in link
        assert "-humanconfidence_web-templates-index.html&" in link


# Step 1, passive.

def test_passive_is_read_from_the_answer_of_the_cloud(cloud):
    cloud()
    response = client_for().get(
        "/passive", headers={"User-Agent": DESKTOP_CHROME})

    assert response.status_code == 200
    assert response.get_json() == {
        "source": "Passive", "humanConfidence": "Medium"}


def test_passive_passes_on_the_headers_the_cloud_lists_and_the_address(
        cloud):
    stub = cloud()
    client_for().get("/passive", headers={
        "User-Agent": DESKTOP_CHROME,
        "Sec-CH-UA": '"Chromium";v="120"',
        "Authorization": "Bearer a-secret",
        "Cookie": "session=a-secret"})

    method, url, data = stub.requests[-1]
    assert method == "POST"
    assert url == API + RESOURCE_KEY + ".json"
    # The values as the browser sent them, under the names the cloud
    # lists, with the address of the connection. Nothing else is sent.
    assert data == {
        "user-agent": DESKTOP_CHROME,
        "sec-ch-ua": '"Chromium";v="120"',
        "client-ip": "127.0.0.1"}


def test_address_of_the_connection_replaces_one_a_header_names(cloud):
    stub = cloud()
    stub.instead["evidencekeys"] = StubResponse(
        ["header.user-agent", "header.client-ip"])
    client_for().get("/passive", headers={
        "User-Agent": DESKTOP_CHROME, "Client-IP": "203.0.113.9"})

    assert stub.requests[-1][2]["client-ip"] == "127.0.0.1"


def test_list_of_headers_is_asked_for_once(cloud):
    stub = cloud()
    client = client_for()
    client.get("/passive")
    client.get("/passive")

    assert len(stub.sent_to("evidencekeys")) == 1
    assert len(stub.sent_to(".json")) == 2


def test_passive_never_sends_the_licence_key(cloud):
    stub = cloud()
    client_for().get("/passive")

    for _, url, data in stub.requests:
        assert LICENCE_KEY not in url
        assert LICENCE_KEY not in data.values()


def test_passive_without_the_properties_returns_neither(cloud):
    stub = cloud()
    stub.instead[".json"] = StubResponse({"device": {"ismobile": False}})

    assert client_for().get("/passive").get_json() == {
        "source": None, "humanConfidence": None}


# What the live tests ask of the key before they assert on a value.

def test_key_carries_a_property_the_cloud_lists_for_it(cloud):
    cloud(properties=("HumanConfidence",))

    assert key_carries(API, RESOURCE_KEY, "HumanConfidence")
    assert key_carries(API, RESOURCE_KEY, "humanconfidence")


def test_key_does_not_carry_a_property_the_cloud_leaves_out(cloud):
    stub = cloud(properties=("HumanConfidence",))

    assert not key_carries(API, RESOURCE_KEY, "HumanConfidenceSource")
    method, url, _ = stub.requests[0]
    assert method == "GET"
    assert url == API + "accessibleproperties?resource=" + RESOURCE_KEY


def test_key_carries_stops_when_the_cloud_refuses_the_key(cloud):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = \
        StubResponse('{"errors":["The resource key is not valid."]}', 400)

    with pytest.raises(ValueError, match="The resource key is not valid."):
        key_carries(API, RESOURCE_KEY, "HumanConfidence")


def test_passive_says_what_the_cloud_refused(cloud):
    stub = cloud()
    stub.instead[".json"] = StubResponse(
        '{"errors":["The resource key is not valid."]}', 400)
    answer = client_for().get("/passive").get_json()

    assert answer["error"].startswith("HTTP 400: ")
    assert "The resource key is not valid." in answer["error"]


def test_passive_answers_when_the_cloud_cannot_be_reached(cloud):
    stub = cloud()
    stub.instead[".json"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    response = client_for().get("/passive")

    assert response.status_code == 200
    assert "cannot be reached" in response.get_json()["error"]


# Step 3, redeem.

def test_redeem_sends_the_sealed_value_with_the_licence_key(cloud):
    stub = cloud()
    response = client_for().post("/redeem", data={"value": "a-sealed-value"})

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.get_json() == {
        "humanConfidence": "High", "secondsSinceVerified": 2}
    method, url, data = stub.requests[-1]
    assert method == "POST"
    assert url == API + "hc/redeem"
    assert data == {"value": "a-sealed-value", "license": LICENCE_KEY}


def test_second_redeem_of_the_same_value_is_replayed(cloud):
    cloud()
    client = client_for()
    first = client.post("/redeem", data={"value": "a-sealed-value"})
    second = client.post("/redeem", data={"value": "a-sealed-value"})

    assert first.get_json()["humanConfidence"] == "High"
    assert second.get_json() == {"result": "replayed"}


def test_redeem_without_a_licence_key_sends_none(cloud):
    stub = cloud()
    client_for(license_key="").post(
        "/redeem", data={"value": "a-sealed-value"})

    assert stub.requests[-1][2] == {"value": "a-sealed-value"}


def test_redeem_gives_the_answer_as_the_cloud_gave_it(cloud):
    stub = cloud()
    stub.instead["hc/redeem"] = StubResponse('{"result":"expired"}', 400)
    response = client_for().post("/redeem", data={"value": "a-sealed-value"})

    assert response.status_code == 400
    assert response.get_data(as_text=True) == '{"result":"expired"}'


def test_redeem_says_when_the_service_does_not_redeem(cloud):
    stub = cloud()
    stub.instead["hc/redeem"] = StubResponse("Not Found", 404)
    response = client_for().post("/redeem", data={"value": "a-sealed-value"})

    assert response.get_json() == {
        "error": f"The service at {API} doesn't redeem Human Confidence."}


def test_redeem_answers_502_when_the_cloud_cannot_be_reached(cloud):
    stub = cloud()
    stub.instead["hc/redeem"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    response = client_for().post("/redeem", data={"value": "a-sealed-value"})

    assert response.status_code == 502
    assert "cannot be reached" in response.get_json()["error"]


# The cloud address.

def test_cloud_address_defaults_to_the_public_cloud():
    assert example.api_base("") == "https://cloud.51degrees.com/api/v4/"
    assert example.api_base(None) == "https://cloud.51degrees.com/api/v4/"


@pytest.mark.parametrize("named", [
    "https://cloud.example.test/api/v4",
    "https://cloud.example.test/api/v4/",
    " https://cloud.example.test/api/v4// "])
def test_cloud_address_named_ends_in_one_slash(named):
    assert example.api_base(named) == \
        "https://cloud.example.test/api/v4/"


# Before the flow.

class Started(Exception):
    """Raised in place of starting the web server."""


@pytest.fixture
def start(monkeypatch):
    """Runs main with the settings given and no others but the address of
    the stand-in for the cloud service, with a stand-in for the web server,
    and returns what create_app and run were given, or None when the server
    was not started."""

    def run_main(argv=(), **settings):
        for name in SETTINGS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(ExampleUtils.CLOUD_ENDPOINT_ENV_VAR, API)
        for name, value in settings.items():
            monkeypatch.setenv(name, value)
        given = {}

        class Server:

            def run(self, **arguments):
                given["run"] = arguments
                raise Started()

        def create_app(*arguments):
            given["create_app"] = arguments
            return Server()

        monkeypatch.setattr(example, "create_app", create_app)
        try:
            example.main(list(argv))
        except Started:
            return given
        return None

    return run_main


def assert_ends_with_find_out_more(printed):
    assert "Find out more:" in printed
    for _, url in example.FIND_OUT_MORE:
        assert url in printed
    links = LINK.findall(printed.split("Find out more:", 1)[1])
    assert links
    for link in links:
        assert TAGS + "find-out-more" in link


def test_starts_when_the_key_carries_human_confidence(cloud, start, capsys):
    stub = cloud()
    given = start(**{
        ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY,
        ExampleUtils.LICENSE_KEY_ENV_VAR: LICENCE_KEY,
        ExampleUtils.CLOUD_ENDPOINT_ENV_VAR: API.rstrip("/")})

    assert given["create_app"] == (RESOURCE_KEY, LICENCE_KEY, API)
    assert given["run"] == {"port": 5151}
    # The key was checked with the cloud named, before anything else.
    method, url, _ = stub.requests[0]
    assert method == "GET"
    assert url == API + "accessibleproperties?resource=" + RESOURCE_KEY
    assert f"http://localhost:5151/, using {API}" in capsys.readouterr().out


def test_listens_on_the_port_named(cloud, start):
    cloud()
    given = start(**{
        "_51DEGREES_EXAMPLE_HTTP_PORTS": "8080",
        ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    assert given["run"] == {"port": 8080}


def test_resource_key_can_be_the_first_argument(cloud, start):
    cloud()
    given = start([RESOURCE_KEY])

    assert given["create_app"][0] == RESOURCE_KEY


def test_starts_without_a_licence_key_and_says_so(cloud, start, capsys):
    cloud()
    given = start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    assert given is not None
    assert ExampleUtils.LICENSE_KEY_ENV_VAR in capsys.readouterr().out


def test_without_a_key_says_how_to_get_one_and_ends(start, capsys):
    assert start() is None

    printed = capsys.readouterr().out
    assert ExampleUtils.RESOURCE_KEY_ENV_VAR in printed
    assert "https://51degrees.com/configure" + TAGS in printed
    assert_ends_with_find_out_more(printed)


def test_key_without_human_confidence_is_given_a_contact_link(
        cloud, start, capsys):
    stub = cloud(properties=("IsMobile",))

    with pytest.raises(SystemExit):
        start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    printed = capsys.readouterr().out
    assert "https://51degrees.com/contact-us" + TAGS in printed
    assert_ends_with_find_out_more(printed)
    # Nothing was asked of the cloud beyond what the key carries.
    assert len(stub.requests) == 1


def test_key_the_cloud_refuses_ends_with_what_the_cloud_said(
        cloud, start, capsys):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = \
        StubResponse('{"errors":["The resource key is not valid."]}', 400)

    with pytest.raises(SystemExit):
        start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    printed = capsys.readouterr().out
    assert "The resource key is not valid." in printed
    assert_ends_with_find_out_more(printed)


def test_cloud_that_cannot_be_reached_ends_saying_so(cloud, start, capsys):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = \
        requests.exceptions.ConnectionError(
            "The stand-in service cannot be reached.")

    with pytest.raises(SystemExit):
        start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    printed = capsys.readouterr().out
    assert "cannot be reached" in printed
    assert_ends_with_find_out_more(printed)


def test_property_is_found_whichever_product_holds_it(cloud):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = \
        StubResponse({"Products": {
            "device": {"Properties": [{"Name": "IsMobile"}]},
            "another": {"Properties": [{"Name": "humanconfidence"}]}}})

    assert example.carries_human_confidence(API, RESOURCE_KEY) is True

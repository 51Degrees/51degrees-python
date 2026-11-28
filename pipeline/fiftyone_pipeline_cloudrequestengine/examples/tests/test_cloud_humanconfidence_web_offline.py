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
import os
import re
import shutil
import subprocess
import urllib.parse

import pytest
import requests

from fiftyone_pipeline_examples.cloud.humanconfidence_web import (
    app as example)
from fiftyone_pipeline_examples.example_utils import ExampleUtils

import test_cloud_humanconfidence_web as live

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
        # The sealed results already sent in a JSON call.
        self.redeemed = set()
        # The derived section answered for a sealed result sent the first
        # time.
        self.sealed_answer = {
            "humanconfidence": "High", "humanconfidencesource": "Active"}
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

        # The example asks with a GET and the Cloud Request Engine, which
        # holds a License Key, with a POST that spells it accessibleProperties.
        if path.lower().startswith("accessibleproperties"):
            return StubResponse({"Products": {"derived": {"Properties": [
                {"Name": name, "Type": "String"}
                for name in self.properties]}}})

        if path == "evidencekeys":
            return StubResponse([
                "header.user-agent", "header.sec-ch-ua", "query.client-ip"])

        if path.split("?")[0] == RESOURCE_KEY + ".json":
            # A JSON call that carries a sealed result is answered with
            # sealed_answer, the first time that sealed result is sent.
            if "humanconfidence" in data and \
                    data["humanconfidence"] not in self.redeemed:
                self.redeemed.add(data["humanconfidence"])
                return StubResponse({"derived": self.sealed_answer})
            return StubResponse({"derived": {
                "humanconfidence": "Medium",
                "humanconfidencesource": "Passive"}})

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

SCRIPT_URL = re.compile(r'var SCRIPT_URL = "([^"]+)";')
PAGE_ID = re.compile(r'var PAGE = "([^"]+)";')


def page_of(client):
    """The script address and the page id a page load gives."""
    html = client.get("/").get_data(as_text=True)
    return SCRIPT_URL.search(html).group(1), PAGE_ID.search(html).group(1)


def transaction_of(script_url):
    query = urllib.parse.urlparse(script_url).query
    return urllib.parse.parse_qs(query)["transaction"][0]


def test_page_carries_the_script_address_the_package_gives(cloud):
    cloud()
    client = client_for()
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Human Confidence demo" in html
    script_url, page_id = page_of(client)
    # The address of the cloud's client script for the Resource Key, with
    # the transaction the package issued for the page.
    assert script_url.startswith(
        API + RESOURCE_KEY + ".js?transaction=")
    assert transaction_of(script_url)
    assert page_id
    assert transaction_of(script_url) not in page_id
    assert '<link rel="stylesheet" href="/css/examples-main.min.css">' in html
    assert client.get("/css/examples-main.min.css").status_code == 200


def test_each_page_load_gets_its_own_transaction(cloud):
    cloud()
    client = client_for()
    first, second = page_of(client), page_of(client)
    assert transaction_of(first[0]) != transaction_of(second[0])
    assert first[1] != second[1]


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


# The Basic product does not offer HumanConfidenceSource, so a Basic key is
# answered with no source, and with or without a level. The example gives
# what the cloud gave and makes up neither.
@pytest.mark.parametrize("level", [None, "Medium"])
def test_passive_for_a_basic_key_returns_no_source(cloud, level):
    stub = cloud()
    derived = {
        "humanconfidence": level,
        "humanconfidencesource": None,
        "humanconfidencesourcenullreason":
            "The key does not give this property a value."}
    if level is None:
        derived["humanconfidencenullreason"] = (
            "The key does not give this property a value.")
    stub.instead[".json"] = StubResponse({"derived": derived})

    assert client_for().get("/passive").get_json() == {
        "source": None, "humanConfidence": level}


# With no Basic key set, the live test skips, naming the variable it reads
# and what a Basic key is there to check.
def test_the_live_basic_key_test_skips_naming_its_variable(monkeypatch):
    monkeypatch.delenv(live.BASIC_KEY_NAME, raising=False)

    with pytest.raises(pytest.skip.Exception) as skipped:
        live.test_a_basic_key_gets_no_source(API, None)

    assert live.BASIC_KEY_NAME == "_51DEGREES_RESOURCE_KEY_BASIC"
    assert f"{live.BASIC_KEY_NAME} is not set" in str(skipped.value)
    assert ("The Basic product does not offer HumanConfidenceSource"
            in str(skipped.value))


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


# Step 3, read on the server. The page sends the sealed result back, and the
# example reads the two properties through its pipeline, whose Cloud
# Request Engine redeems it. The example never redeems a sealed result
# itself.

EXAMPLE_FILES = [
    example.__file__,
    os.path.join(os.path.dirname(example.__file__), "templates",
                 "index.html")]


def send(client, sealed="a-sealed-value", page_id=None):
    """Loads the page, then sends the sealed result with its page id, as
    the page does. Gives the answer and the page's script address."""
    script_url, issued = page_of(client)
    response = client.post("/humanconfidence", data={
        "humanconfidence": sealed,
        "humanconfidencepage": issued if page_id is None else page_id})
    assert response.status_code == 200
    return response.get_json(), script_url


def test_the_example_never_redeems_a_sealed_result_itself():
    for path in EXAMPLE_FILES:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        assert "hc/redeem" not in text, path
        assert "sealedResult" not in text, path


def test_the_package_redeems_through_the_json_call(cloud):
    stub = cloud()
    answer, script_url = send(client_for())

    assert answer == {"source": "Active", "humanConfidence": "High",
                      "humanConfidenceNullReason": None}
    assert stub.sent_to("hc/redeem") == []
    method, url, data = stub.sent_to(".json?")[-1]
    assert method == "POST"
    assert url == API + RESOURCE_KEY + ".json?"
    # The sealed result as the page sent it, the transaction the package
    # kept for the page, and the License Key, which only this server holds.
    assert data["humanconfidence"] == "a-sealed-value"
    assert data["transaction"] == transaction_of(script_url)
    assert data["license"] == LICENCE_KEY
    assert "humanconfidencepage" not in data


def test_the_example_shows_the_value_the_package_gives(cloud):
    stub = cloud()
    stub.sealed_answer = {
        "humanconfidence": "Low", "humanconfidencesource": "Active"}

    assert send(client_for())[0]["humanConfidence"] == "Low"


def test_a_sealed_result_sent_again_is_not_redeemed_again(cloud):
    stub = cloud()
    client = client_for()
    script_url, page_id = page_of(client)
    form = {"humanconfidence": "a-sealed-value",
            "humanconfidencepage": page_id}
    first = client.post("/humanconfidence", data=form).get_json()
    second = client.post("/humanconfidence", data=form).get_json()

    assert first["humanConfidence"] == "High"
    assert second == {"source": "Active", "humanConfidence": "Medium",
                      "humanConfidenceNullReason": None}
    # The transaction was used, so the package did not send the sealed
    # result again.
    assert "humanconfidence" not in stub.sent_to(".json?")[-1][2]


def test_a_page_the_package_did_not_serve_is_not_redeemed(cloud):
    stub = cloud()
    answer, _ = send(client_for(), page_id="a-page-never-served")

    assert answer["source"] == "Active"
    assert answer["humanConfidence"] == "Medium"
    assert "humanconfidence" not in stub.sent_to(".json?")[-1][2]


def test_without_a_licence_key_nothing_is_redeemed(cloud):
    stub = cloud()
    answer, _ = send(client_for(license_key=""))

    assert answer["humanConfidence"] == "Medium"
    sent = stub.sent_to(".json?")[-1][2]
    assert "humanconfidence" not in sent
    assert "license" not in sent


def test_a_cloud_that_cannot_be_reached_gives_medium(cloud):
    stub = cloud()
    client = client_for()
    # The pipeline is built on the first request, so the failure is put in
    # place after that.
    send(client)
    stub.instead[".json?"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    answer, _ = send(client, sealed="another-sealed-value")

    assert answer["source"] == "Active"
    assert answer["humanConfidence"] == "Medium"


# Each answer the server can give the page, with the text the page shows
# for the level. With no level the page shows why, as the null reason.
READ_ANSWERS = [
    ({"source": "Active", "humanConfidence": "High",
      "humanConfidenceNullReason": None}, "High"),
    ({"source": "Active", "humanConfidence": "Medium",
      "humanConfidenceNullReason": None}, "Medium"),
    ({"source": None, "humanConfidence": None,
      "humanConfidenceNullReason": "The key does not carry this property."},
     "The key does not carry this property."),
    ({"source": "Active"}, "no level"),
    ({"error": "HTTP 502"}, "no level"),
]


@pytest.mark.skipif(shutil.which("node") is None,
                    reason="Node is not on the path")
def test_page_shows_the_null_reason_where_there_is_no_level():
    template = os.path.join(
        os.path.dirname(example.__file__), "templates", "index.html")
    with open(template, encoding="utf-8") as handle:
        page = handle.read()
    functions = []
    for name in ("levelClass", "showRead"):
        found = re.search(
            r"function " + name + r"\(.*?\n  \}", page, re.S)
        assert found is not None, "the page has a " + name + " function"
        functions.append(found.group(0))
    script = (
        "var PASS = 'pass', FAIL = 'fail', PART = 'part', NONE = 'none';\n"
        "var shown = {};\n"
        "function show(id, text, cls) { shown[id] = text; }\n"
        + "\n".join(functions)
        + "\nconsole.log(JSON.stringify("
        + json.dumps([answer for answer, _ in READ_ANSWERS])
        + ".map(function (answer) { shown = {}; showRead(answer); "
        "return shown['redeem-level']; })));\n")
    finished = subprocess.run(
        [shutil.which("node"), "-e", script], capture_output=True,
        text=True, timeout=60)
    assert finished.returncode == 0, finished.stderr

    assert json.loads(finished.stdout) == [
        expected for _, expected in READ_ANSWERS]


def test_the_licence_key_never_reaches_the_page_after_a_read(cloud):
    cloud()
    client = client_for()
    response = client.post("/humanconfidence", data={
        "humanconfidence": "a-sealed-value"})
    assert LICENCE_KEY not in response.get_data(as_text=True)


def test_no_part_of_the_licence_key_reaches_the_page_when_building_fails(
        cloud, caplog):
    stub = cloud()
    key = "LK-0123456789-WXYZ"
    # The cloud refuses the key and names it, so the pipeline isn't built.
    refusal = StubResponse(
        {"errors": ["The license key " + key + " is not valid."]}, 403)
    refusal.headers = {}
    refusal.url = API + "accessibleProperties"
    stub.instead["accessibleProperties"] = refusal
    with caplog.at_level("ERROR"):
        response = client_for(license_key=key).post(
            "/humanconfidence", data={"humanconfidence": "a-sealed-value"})
    page = response.get_data(as_text=True)

    parts = {key[i:i + 4] for i in range(len(key) - 3)}
    assert [part for part in parts if part in page] == []
    assert "not valid" not in page
    # The details go to the server's log, still without the key.
    assert caplog.records
    assert [part for part in parts if part in caplog.text] == []


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

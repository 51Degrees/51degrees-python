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
stand-in answers in the shapes the example and the cloud request engine
read, and keeps the requests it was sent, so the tests see what was passed
on.
"""

import json
import logging
import re

import pytest
import requests

from fiftyone_pipeline_examples.cloud.humanconfidence_web import (
    app as example)
from fiftyone_pipeline_examples.example_utils import ExampleUtils

import test_cloud_humanconfidence_web as live

API = "https://cloud.example/api/v4/"
# A private cloud, such as one in Docker, on plain http.
PRIVATE_API = "http://127.0.0.1:18081/api/v4/"
RESOURCE_KEY = "a-resource-key"
LICENSE_KEY = "a-license-key"

# A public address, and the address the test client connects from.
PUBLIC_ADDRESS = "81.2.69.142"
LOCAL_ADDRESS = "127.0.0.1"

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


class StubHeaders(dict):
    """Response headers, with getlist as urllib3 gives it."""

    def __init__(self, items=()):
        super().__init__()
        self.items_list = list(items)
        for name, value in self.items_list:
            self[name] = value

    def getlist(self, name):
        return [value for key, value in self.items_list
                if key.lower() == name.lower()]


class StubRaw:

    def __init__(self, headers):
        self.headers = headers


class StubResponse:

    def __init__(self, body, status_code=200, headers=(), url=""):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)
        self.content = self.text.encode()
        self.headers = StubHeaders(headers)
        self.raw = StubRaw(self.headers)
        self.url = url

    def json(self):
        return json.loads(self.text)


class StubCloud:
    """
    Answers as the cloud service does for a key carrying the named
    properties, and keeps the requests it was sent as method, address and
    form fields. The other arguments of each request are kept in calls.
    """

    def __init__(self, properties, api=API):
        self.properties = properties
        self.api = api
        self.requests = []
        self.calls = []
        # The sealed values already redeemed, as each redeems once.
        self.redeemed = set()
        # An answer to give in place of the usual one, by the end of the
        # address, as a StubResponse or an exception to raise.
        self.instead = {}
        # The client script the cloud serves for the Resource Key.
        self.script = "/* client script */"

    def sent_to(self, ending):
        """The requests sent to the addresses with the ending, the query
        left out."""
        return [sent for sent in self.requests
                if sent[1].split("?")[0].endswith(ending)]

    def request(self, method, url, data=None, headers=None, timeout=None,
                params=None, **others):
        data = dict(data or {})
        self.requests.append((method, url, data))
        self.calls.append({"method": method, "url": url, "data": data,
                           "headers": dict(headers or {}),
                           "timeout": timeout, "params": params})
        path = url[len(self.api):] if url.startswith(self.api) else url
        bare = path.split("?")[0]

        for ending, answer in self.instead.items():
            if path.endswith(ending) or bare.endswith(ending):
                if isinstance(answer, BaseException):
                    raise answer
                return answer

        # The example asks in lower case, the cloud request engine in
        # camel case. The cloud service takes either.
        if bare.lower() == "accessibleproperties":
            return StubResponse({"Products": {"derived": {"Properties": [
                {"Name": name, "Type": "String"}
                for name in self.properties]}}}, url=url)

        if bare == "evidencekeys":
            return StubResponse([
                "header.user-agent", "header.sec-ch-ua", "query.client-ip"],
                url=url)

        if bare == RESOURCE_KEY + ".json" and "humanconfidence" in data:
            # A sealed value redeems once, with a challenge and the License
            # Key, and gives the level as HumanConfidence.
            sealed = data["humanconfidence"]
            if (sealed in self.redeemed or not data.get("challenge")
                    or data.get("license") != LICENSE_KEY):
                return StubResponse({"derived": {
                    "humanconfidence": None,
                    "humanconfidencenullreason": "Not redeemed."}}, url=url)
            self.redeemed.add(sealed)
            return StubResponse(
                {"derived": {"humanconfidence": "High"}}, url=url)

        if bare == RESOURCE_KEY + ".json":
            return StubResponse({"derived": {
                "humanconfidence": "Medium",
                "humanconfidencesource": "Passive"}}, url=url)

        if bare == RESOURCE_KEY + ".js":
            return StubResponse(self.script, url=url, headers=[
                ("Content-Type", "application/javascript")])

        return StubResponse("Not Found", 404, url=url)


@pytest.fixture
def cloud(monkeypatch):
    """Makes a stand-in for the cloud service answer every request."""

    def stand_in(properties=("HumanConfidence", "HumanConfidenceSource"),
                 api=API):
        stub = StubCloud(properties, api)
        monkeypatch.setattr(requests, "request", stub.request)
        return stub

    return stand_in


def client_for(license_key=LICENSE_KEY, api=API):
    return example.create_app(RESOURCE_KEY, license_key, api).test_client()


def from_address(address):
    """The arguments that make the test client connect from address."""
    return {"environ_base": {"REMOTE_ADDR": address}}


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
    stylesheet = client.get("/css/examples-main.min.css")
    stylesheet.close()
    assert stylesheet.status_code == 200


def test_page_is_never_kept_by_a_cache(cloud):
    cloud()
    assert client_for().get("/").headers["Cache-Control"] == "no-store"


def test_building_the_app_asks_the_cloud_what_the_key_carries(cloud):
    stub = cloud()
    client_for()

    assert [(method, url) for method, url, _ in stub.requests] == [
        ("GET", API + "accessibleProperties?resource=" + RESOURCE_KEY),
        ("GET", API + "evidencekeys")]


def test_page_is_served_without_asking_the_cloud_again(cloud):
    stub = cloud()
    client = client_for()
    asked = len(stub.requests)
    client.get("/")

    assert len(stub.requests) == asked


def test_license_key_never_reaches_the_page(cloud):
    cloud()
    for mode in ("client", "server"):
        html = client_for().get("/?mode=" + mode).get_data(as_text=True)
        assert LICENSE_KEY not in html


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


def test_page_redeems_only_a_sealed_value_and_waits_30_seconds(cloud):
    cloud()
    html = client_for().get("/").get_data(as_text=True)

    assert 'var PLAIN = LEVELS.concat(["Unknown"]);' in html
    assert "PLAIN.indexOf(value) < 0" in html
    assert "var ACTIVE_LIMIT_MS = 30000;" in html


# The mode.

def test_mode_is_client_side_by_default_and_kept_in_a_cookie(cloud):
    cloud()
    response = client_for().get("/")

    assert 'var MODE = "client";' in response.get_data(as_text=True)
    assert "hc_mode=client" in response.headers["Set-Cookie"]


def test_mode_named_is_used_and_kept(cloud):
    cloud()
    client = client_for()
    named = client.get("/?mode=server")
    kept = client.get("/")

    assert 'var MODE = "server";' in named.get_data(as_text=True)
    assert "hc_mode=server" in named.headers["Set-Cookie"]
    assert 'var MODE = "server";' in kept.get_data(as_text=True)


def test_mode_not_known_gives_the_default(cloud):
    cloud()
    html = client_for().get("/?mode=other").get_data(as_text=True)

    assert 'var MODE = "client";' in html


# Passive.

def test_passive_is_read_from_the_answer_of_the_cloud(cloud):
    cloud()
    response = client_for().get(
        "/passive", headers={"User-Agent": DESKTOP_CHROME})
    answer = response.get_json()

    assert response.status_code == 200
    assert answer["humanConfidence"] == "Medium"
    assert set(answer) == {"humanConfidence", "sent"}


def test_passive_goes_through_the_cloud_request_engine(cloud):
    stub = cloud()
    client_for().get("/passive", headers={
        "User-Agent": DESKTOP_CHROME,
        "Sec-CH-UA": '"Chromium";v="120"',
        "Authorization": "Bearer a-secret",
        "Cookie": "session=a-secret"})

    method, url, data = stub.requests[-1]
    assert method == "POST"
    assert url.split("?")[0] == API + RESOURCE_KEY + ".json"
    # The values as the browser sent them, under the names the cloud
    # lists, with the Resource Key the engine adds. Nothing else is sent.
    assert data == {
        "user-agent": DESKTOP_CHROME,
        "sec-ch-ua": '"Chromium";v="120"',
        "resource": RESOURCE_KEY}


def test_passive_describes_what_was_sent(cloud):
    cloud()
    sent = client_for().get(
        "/passive", headers={"User-Agent": DESKTOP_CHROME},
        **from_address(PUBLIC_ADDRESS)).get_json()["sent"]

    assert sent["method"] == "POST"
    assert sent["url"] == API + RESOURCE_KEY + ".json"
    assert dict(sent["form"]) == {
        "user-agent": DESKTOP_CHROME, "client-ip": PUBLIC_ADDRESS}


def test_public_address_of_the_connection_is_sent(cloud):
    stub = cloud()
    client_for().get(
        "/passive", headers={"User-Agent": DESKTOP_CHROME},
        **from_address(PUBLIC_ADDRESS))

    assert stub.requests[-1][2]["client-ip"] == PUBLIC_ADDRESS


def test_ipv4_address_written_as_ipv6_is_sent_as_ipv4(cloud):
    stub = cloud()
    client_for().get(
        "/passive", headers={"User-Agent": DESKTOP_CHROME},
        **from_address("::ffff:" + PUBLIC_ADDRESS))

    assert stub.requests[-1][2]["client-ip"] == PUBLIC_ADDRESS


def test_public_address_replaces_one_a_header_names(cloud):
    stub = cloud()
    stub.instead["evidencekeys"] = StubResponse(
        ["header.user-agent", "header.client-ip"])
    client_for().get(
        "/passive",
        headers={"User-Agent": DESKTOP_CHROME, "Client-IP": "203.0.113.9"},
        **from_address(PUBLIC_ADDRESS))

    assert stub.requests[-1][2]["client-ip"] == PUBLIC_ADDRESS


def test_local_connection_sends_no_address(cloud):
    stub = cloud()
    stub.instead["evidencekeys"] = StubResponse(
        ["header.user-agent", "header.client-ip"])
    sent = client_for().get(
        "/passive",
        headers={"User-Agent": DESKTOP_CHROME, "Client-IP": "203.0.113.9"},
        **from_address(LOCAL_ADDRESS)).get_json()["sent"]

    assert stub.requests[-1][2] == {
        "user-agent": DESKTOP_CHROME, "resource": RESOURCE_KEY}
    assert sent["form"] == [["user-agent", DESKTOP_CHROME]]


def test_address_comes_only_from_the_connection(cloud):
    stub = cloud()
    client_for().post(
        "/hc/cloud/cloud.example/api/v4/" + RESOURCE_KEY + ".json",
        headers={"User-Agent": DESKTOP_CHROME},
        data={"client-ip": "203.0.113.9", "fod-test": "an-answer"},
        **from_address(PUBLIC_ADDRESS))

    assert stub.requests[-1][2]["client-ip"] == PUBLIC_ADDRESS


def test_described_form_is_what_the_engine_sent(cloud):
    stub = cloud()
    stub.instead["evidencekeys"] = StubResponse(
        ["header.user-agent", "header.client-ip", "header.sec-ch-ua"])
    sent = client_for().get(
        "/passive",
        headers={"User-Agent": DESKTOP_CHROME, "Client-IP": "203.0.113.9",
                 "Sec-CH-UA": '"Chromium";v="120"'},
        **from_address(PUBLIC_ADDRESS)).get_json()["sent"]

    names = [name for name, _ in sent["form"]]
    assert len(names) == len(set(names))
    engine_sent = dict(stub.requests[-1][2])
    del engine_sent["resource"]
    assert dict(sent["form"]) == engine_sent


def test_list_of_headers_is_the_one_the_engine_was_given(cloud):
    stub = cloud()
    client = client_for()
    client.get("/passive")
    client.get("/passive")
    client.get("/hc/script.js")

    assert len(stub.sent_to("evidencekeys")) == 1
    assert len(stub.sent_to("accessibleProperties")) == 1
    assert len(stub.sent_to(".json")) == 2


def test_engine_waits_the_example_timeout(cloud):
    stub = cloud()
    client_for().get("/passive")

    engine_calls = [call for call in stub.calls
                    if "accessibleProperties" in call["url"]
                    or call["url"].endswith("evidencekeys")
                    or call["url"].split("?")[0].endswith(".json")]
    assert len(engine_calls) == 3
    for call in engine_calls:
        assert call["timeout"] == example.TIMEOUT


def test_list_of_headers_the_cloud_cannot_give_is_an_error(cloud):
    stub = cloud()
    stub.instead["evidencekeys"] = StubResponse("Unavailable", 503)
    with pytest.warns(UserWarning):
        client = client_for()

    assert "error" in client.get("/passive").get_json()
    assert client.get("/hc/script.js").status_code == 502
    assert client.get(
        "/hc/cloud/cloud.example/api/v4/3pc").status_code == 502


def test_passive_never_sends_the_license_key(cloud):
    stub = cloud()
    client_for().get("/passive")

    for _, url, data in stub.requests:
        assert LICENSE_KEY not in url
        assert LICENSE_KEY not in data.values()


def test_passive_without_the_property_returns_no_level(cloud):
    stub = cloud()
    stub.instead[".json"] = StubResponse({"device": {"ismobile": False}})

    assert client_for().get("/passive").get_json()["humanConfidence"] is None


# The Basic product does not offer HumanConfidenceSource, so a Basic key is
# answered with no source, and with or without a level. The example gives
# the level the cloud gave and makes up none.
@pytest.mark.parametrize("level", [None, "Medium"])
def test_passive_for_a_basic_key_gives_the_level_the_cloud_gave(
        cloud, level):
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

    assert client_for().get("/passive").get_json()["humanConfidence"] == \
        level


# With no Basic key set, the live test skips, naming the variable it reads.
def test_the_live_basic_key_test_skips_naming_its_variable(monkeypatch):
    monkeypatch.delenv(live.BASIC_KEY_NAME, raising=False)

    with pytest.raises(pytest.skip.Exception) as skipped:
        live.test_a_basic_key_gets_a_passive_level(API, None)

    assert live.BASIC_KEY_NAME == "_51DEGREES_RESOURCE_KEY_BASIC"
    assert f"{live.BASIC_KEY_NAME} is not set" in str(skipped.value)


def test_passive_says_what_the_cloud_refused(cloud):
    stub = cloud()
    stub.instead[".json"] = StubResponse(
        '{"errors":["The resource key is not valid."]}', 400)
    answer = client_for().get("/passive").get_json()

    assert "The resource key is not valid." in answer["error"]


def test_passive_answers_when_the_cloud_cannot_be_reached(cloud):
    stub = cloud()
    stub.instead[".json"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    response = client_for().get("/passive")

    assert response.status_code == 200
    assert "cannot be reached" in response.get_json()["error"]


# Active.

SEALED = "a-sealed-value"


def page_values(client, mode="client"):
    """The challenge and page value the page was given."""
    html = client.get("/?mode=" + mode).get_data(as_text=True)
    found = re.search(r"var HC = (\{[^;]*\});", html)
    assert found, "The page holds no challenge"
    return json.loads(found.group(1))


def post_active(client, values, sealed=SEALED):
    return client.post("/active", data={
        "humanconfidence": sealed,
        "humanconfidencepage": values["humanconfidencepage"]})


def test_page_is_given_a_new_challenge_each_time(cloud):
    cloud()
    client = client_for()
    first, second = page_values(client), page_values(client)

    assert set(first) == {"challenge", "humanconfidencepage"}
    assert first["challenge"] != second["challenge"]
    assert first["humanconfidencepage"] != second["humanconfidencepage"]


def test_page_asks_for_the_script_with_its_challenge(cloud):
    cloud()
    html = client_for().get("/").get_data(as_text=True)

    assert '+ "?challenge=" + encodeURIComponent(HC.challenge);' in html


def test_active_reads_the_two_properties_the_engine_gives(cloud):
    stub = cloud()
    client = client_for()
    values = page_values(client)
    response = post_active(client, values)

    assert response.status_code == 200
    assert response.get_json() == {
        "humanConfidence": "High", "humanConfidenceSource": "Active"}
    # The cloud request engine redeemed the sealed value through its JSON
    # call, with the challenge the page was given and the License Key.
    method, url, data = stub.requests[-1]
    assert method == "POST"
    assert url.split("?")[0] == API + RESOURCE_KEY + ".json"
    assert data["humanconfidence"] == SEALED
    assert data["challenge"] == values["challenge"]
    assert data["license"] == LICENSE_KEY
    assert "humanconfidencepage" not in data
    assert stub.sent_to("hc/redeem") == []


def test_second_post_of_the_same_page_gives_low(cloud):
    cloud()
    client = client_for()
    values = page_values(client)
    first = post_active(client, values)
    second = post_active(client, values)

    assert first.get_json()["humanConfidence"] == "High"
    assert second.get_json() == {
        "humanConfidence": "Low", "humanConfidenceSource": "Active"}


def test_active_without_a_license_key_gives_low(cloud):
    stub = cloud()
    client = client_for(license_key="")
    response = post_active(client, page_values(client))

    assert response.get_json() == {
        "humanConfidence": "Low", "humanConfidenceSource": "Active"}
    assert "humanconfidence" not in stub.requests[-1][2]


def test_active_without_a_sealed_value_is_refused(cloud):
    cloud()
    client = client_for()

    assert post_active(client, page_values(client), "").status_code == 400


@pytest.mark.parametrize("answer", [
    StubResponse('{"errors":["The sealed value was not redeemed."]}', 400),
    StubResponse("Not Found", 404),
    StubResponse({"derived": {"humanconfidence": "Unknown"}}),
    StubResponse({"derived": {"humanconfidence": SEALED}}),
    StubResponse({"device": {"ismobile": False}}),
    requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached."),
    requests.exceptions.Timeout("The stand-in service took too long."),
], ids=["refused", "not-found", "unknown", "not-a-level", "no-derived",
        "unreachable", "timeout"])
def test_value_that_does_not_redeem_gives_low(cloud, answer):
    stub = cloud()
    client = client_for()
    values = page_values(client)
    stub.instead[".json"] = answer
    response = post_active(client, values)

    assert response.status_code == 200
    assert response.get_json() == {
        "humanConfidence": "Low", "humanConfidenceSource": "Active"}


@pytest.mark.parametrize("answer", [
    None,
    StubResponse('{"errors":["The sealed value was not redeemed."]}', 400),
    requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")],
    ids=["redeemed", "refused", "unreachable"])
def test_routes_write_nothing_to_the_console(cloud, capsys, answer):
    stub = cloud()
    client = client_for()
    values = page_values(client)
    if answer is not None:
        stub.instead[".js"] = answer
        stub.instead[".json"] = answer
    client.get("/passive")
    post_active(client, values)
    client.get("/hc/script.js")
    client.post("/hc/cloud/cloud.example/api/v4/" + RESOURCE_KEY + ".json",
                data={"fod-test": "an-answer"})
    client.get("/hc/cloud/cloud.example/api/v4/3pc")

    printed = capsys.readouterr()
    assert printed.out == ""
    assert printed.err == ""


def test_active_waits_the_example_timeout(cloud):
    stub = cloud()
    client = client_for()
    post_active(client, page_values(client))

    assert stub.calls[-1]["timeout"] == example.TIMEOUT


def test_script_is_asked_for_with_the_pages_challenge(cloud):
    stub = cloud()
    client_for().get("/hc/script.js?challenge=a-challenge",
                     **from_address(LOCAL_ADDRESS))

    assert stub.calls[-1]["params"] == {"challenge": "a-challenge"}


# Server mode: the client script.

def test_script_points_each_cloud_address_at_this_server(cloud):
    stub = cloud()
    stub.script = (
        'a("' + API + RESOURCE_KEY + '.json");'
        'b("https://cloud.51degrees.com/api/v4/3pc");'
        'c("https://cloud-eu.51degrees.com/api/v4/x");'
        'd("https://example.com/x");')
    response = client_for().get("/hc/script.js")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(
        "application/javascript")
    assert response.headers["Cache-Control"] == "no-store"
    assert ('a("http://localhost/hc/cloud/cloud.example/api/v4/' +
            RESOURCE_KEY + '.json");') in text
    assert ('b("http://localhost/hc/cloud/cloud.51degrees.com/api/v4/3pc");'
            in text)
    assert ('c("http://localhost/hc/cloud/cloud-eu.51degrees.com/api/v4/x");'
            in text)
    assert 'd("https://example.com/x");' in text


def test_script_is_asked_for_with_the_visitors_headers(cloud):
    stub = cloud()
    client_for().get(
        "/hc/script.js",
        headers={"User-Agent": DESKTOP_CHROME, "Cookie": "session=a-secret",
                 "Authorization": "Bearer a-secret"},
        **from_address(PUBLIC_ADDRESS))
    call = stub.calls[-1]

    assert call["method"] == "GET"
    assert call["url"] == API + RESOURCE_KEY + ".js"
    assert call["params"] == {"client-ip": PUBLIC_ADDRESS}
    assert call["headers"] == {"user-agent": DESKTOP_CHROME}


def test_script_from_a_local_connection_names_no_address(cloud):
    stub = cloud()
    client_for().get("/hc/script.js", **from_address(LOCAL_ADDRESS))

    assert stub.calls[-1]["params"] == {}


def test_script_from_a_private_http_cloud_is_pointed_here(cloud):
    stub = cloud(api=PRIVATE_API)
    stub.script = 'a("' + PRIVATE_API + RESOURCE_KEY + '.json");'
    text = client_for(api=PRIVATE_API).get("/hc/script.js").get_data(
        as_text=True)

    assert ('a("http://localhost/hc/cloud/127.0.0.1:18081/api/v4/' +
            RESOURCE_KEY + '.json");') in text


def test_script_the_cloud_cannot_give_answers_502_with_no_script(cloud):
    stub = cloud()
    stub.instead[".js"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    response = client_for().get("/hc/script.js")

    assert response.status_code == 502
    assert response.get_data(as_text=True) == ""


# Server mode: the calls the client script makes.

def test_test_answers_go_through_the_cloud_request_engine(cloud):
    stub = cloud()
    response = client_for().post(
        "/hc/cloud/cloud.example/api/v4/" + RESOURCE_KEY + ".json",
        headers={"User-Agent": DESKTOP_CHROME},
        data={"resource": "another-key", "values": "x",
              "fod-test": "an-answer"})

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json()["derived"]["humanconfidence"] == "Medium"
    method, url, data = stub.requests[-1]
    assert method == "POST"
    assert url.split("?")[0] == API + RESOURCE_KEY + ".json"
    # The engine sets the Resource Key. The browser's own resource and
    # values fields are left out.
    assert data == {"user-agent": DESKTOP_CHROME, "fod-test": "an-answer",
                    "resource": RESOURCE_KEY}


def test_call_to_a_host_that_is_not_a_cloud_host_is_not_found(cloud):
    stub = cloud()
    client = client_for()
    asked = len(stub.requests)

    for method in ("get", "post"):
        response = getattr(client, method)("/hc/cloud/example.com/x")
        assert response.status_code == 404
    assert len(stub.requests) == asked


def test_get_to_a_cloud_host_is_sent_on_over_https(cloud):
    stub = cloud()
    stub.instead["https://cloud.51degrees.com/api/v4/3pc"] = StubResponse(
        '{"tpc":true}', headers=[("Content-Type", "application/json")])
    response = client_for().get(
        "/hc/cloud/cloud.51degrees.com/api/v4/3pc?a=1",
        headers={"User-Agent": DESKTOP_CHROME})

    assert response.status_code == 200
    assert response.get_json() == {"tpc": True}
    call = stub.calls[-1]
    assert call["url"] == "https://cloud.51degrees.com/api/v4/3pc"
    assert dict(call["params"]) == {"a": "1"}


def test_get_to_a_private_http_cloud_keeps_its_scheme(cloud):
    stub = cloud(api=PRIVATE_API)
    stub.instead["3pc"] = StubResponse("{}")
    response = client_for(api=PRIVATE_API).get(
        "/hc/cloud/127.0.0.1:18081/api/v4/3pc")

    assert response.status_code == 200
    assert stub.calls[-1]["url"] == "http://127.0.0.1:18081/api/v4/3pc"


def test_get_passes_on_only_the_cloud_cookies(cloud):
    stub = cloud()
    stub.instead["3pc"] = StubResponse("{}")
    client = client_for()
    client.set_cookie("51D_id", "one")
    client.set_cookie("session", "a-secret")
    client.get("/hc/cloud/cloud.example/api/v4/3pc",
               headers={"User-Agent": DESKTOP_CHROME})

    assert stub.calls[-1]["headers"] == {
        "user-agent": DESKTOP_CHROME, "Cookie": "51D_id=one"}


def test_get_gives_the_cloud_cookies_for_this_server(cloud):
    stub = cloud()
    stub.instead["3pc"] = StubResponse("{}", headers=[
        ("Set-Cookie",
         "51D_tpc=1; Domain=51degrees.com; Path=/; Secure; SameSite=None"),
        ("Set-Cookie", "51D_two=2; Path=/")])
    response = client_for().get("/hc/cloud/cloud.example/api/v4/3pc")

    assert response.headers.getlist("Set-Cookie") == [
        "51D_tpc=1; Path=/", "51D_two=2; Path=/"]


def test_get_the_cloud_cannot_answer_gives_502(cloud):
    stub = cloud()
    stub.instead["3pc"] = requests.exceptions.ConnectionError(
        "The stand-in service cannot be reached.")
    response = client_for().get("/hc/cloud/cloud.example/api/v4/3pc")

    assert response.status_code == 502


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


@pytest.mark.parametrize("host,matched", [
    ("cloud.51degrees.com", True),
    ("cloud-eu.51degrees.com", True),
    ("127.0.0.1:18081", True),
    ("51degrees.com", False),
    ("cloud.51degrees.com.example", False),
    ("example.com", False)])
def test_cloud_hosts_are_51degrees_hosts_and_the_endpoint_host(
        host, matched):
    hosts, _ = example.cloud_patterns(PRIVATE_API)
    assert bool(hosts.fullmatch(host)) == matched


@pytest.mark.parametrize("address,public", [
    ("81.2.69.142", "81.2.69.142"),
    ("::ffff:81.2.69.142", "81.2.69.142"),
    ("127.0.0.1", None),
    ("10.1.2.3", None),
    ("192.168.1.2", None),
    ("::1", None),
    ("", None),
    (None, None),
    ("not-an-address", None)])
def test_public_ip_gives_only_a_public_address(address, public):
    assert example.public_ip(address) == public


# Before the flow.

class Started(Exception):
    """Raised in place of starting the web server."""


@pytest.fixture
def start(monkeypatch):
    """Runs main with the settings given and no others but the address of
    the stand-in for the cloud service, unless endpoint is None, with a
    stand-in for the web server, and returns what create_app and run were
    given, or None when the server was not started."""

    def run_main(argv=(), endpoint=API, **settings):
        for name in SETTINGS:
            monkeypatch.delenv(name, raising=False)
        if endpoint is not None:
            monkeypatch.setenv(ExampleUtils.CLOUD_ENDPOINT_ENV_VAR, endpoint)
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
        ExampleUtils.LICENSE_KEY_ENV_VAR: LICENSE_KEY,
        ExampleUtils.CLOUD_ENDPOINT_ENV_VAR: API.rstrip("/")})

    assert given["create_app"] == (RESOURCE_KEY, LICENSE_KEY, API)
    assert given["run"] == {"port": 5151, "threaded": True}
    # The key was checked with the cloud named, before anything else.
    method, url, _ = stub.requests[0]
    assert method == "GET"
    assert url == API + "accessibleproperties?resource=" + RESOURCE_KEY
    assert f"http://localhost:5151/, using {API}" in capsys.readouterr().out


def test_cloud_address_is_the_public_cloud_when_none_is_set(cloud, start):
    stub = cloud(api=example.DEFAULT_API)
    given = start(endpoint=None,
                  **{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    assert given["create_app"][2] == example.DEFAULT_API
    assert stub.requests[0][1].startswith(example.DEFAULT_API)


def test_web_server_writes_no_line_for_each_request(cloud, start):
    cloud()
    server_log = logging.getLogger("werkzeug")
    level = server_log.level
    try:
        start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})
        # The web server sets its own level to INFO only when none is set.
        assert server_log.level == logging.WARNING
    finally:
        server_log.setLevel(level)


def test_listens_on_the_port_named(cloud, start):
    cloud()
    given = start(**{
        "_51DEGREES_EXAMPLE_HTTP_PORTS": "8080",
        ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    assert given["run"] == {"port": 8080, "threaded": True}


def test_resource_key_can_be_the_first_argument(cloud, start):
    cloud()
    given = start([RESOURCE_KEY])

    assert given["create_app"][0] == RESOURCE_KEY


def test_starts_without_a_license_key_and_says_so(cloud, start, capsys):
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


@pytest.mark.parametrize("failure", [
    requests.exceptions.ConnectionError(
        "Max retries exceeded with url: /api/v4/accessibleproperties"
        "?resource=" + RESOURCE_KEY + " (cannot be reached)"),
    StubResponse('{"errors":["The resource key ' + RESOURCE_KEY +
                 ' is not valid."]}', 400)],
    ids=["unreachable", "refused"])
def test_start_up_error_shows_the_resource_key_as_its_name(
        cloud, start, capsys, failure):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = failure

    with pytest.raises(SystemExit):
        start(**{ExampleUtils.RESOURCE_KEY_ENV_VAR: RESOURCE_KEY})

    printed = capsys.readouterr().out
    assert RESOURCE_KEY not in printed
    assert "<Resource Key>" in printed


def test_property_is_found_whichever_product_holds_it(cloud):
    stub = cloud()
    stub.instead["accessibleproperties?resource=" + RESOURCE_KEY] = \
        StubResponse({"Products": {
            "device": {"Properties": [{"Name": "IsMobile"}]},
            "another": {"Properties": [{"Name": "humanconfidence"}]}}})

    assert example.carries_human_confidence(API, RESOURCE_KEY) is True

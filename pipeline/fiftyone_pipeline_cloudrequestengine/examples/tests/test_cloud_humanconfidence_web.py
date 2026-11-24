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
Runs the Human Confidence web example against the cloud service through
Flask's test client. The resource key has to carry HumanConfidence, which
the example asks the cloud service about before anything else, and these
tests skip themselves when no key is set or the key does not carry it.

The passive tests check that the example gives a level from the cloud's
answer, and describes the request it sent. A Basic key, whose product does
not offer HumanConfidenceSource, gets a level when the cloud says it
carries HumanConfidence, and is otherwise given the contact link when the
example starts.

Only the passive step is run here. The active step needs the browser tests,
which only a browser runs.
"""

import pytest
import requests

from fiftyone_pipeline_examples.cloud.humanconfidence_web import (
    app as example)
from fiftyone_pipeline_examples.example_utils import ExampleUtils

from live_cloud import (
    RESOURCE_KEY_NAMES, find_resource_key, read_environment)

DESKTOP_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

HEADERS = {"User-Agent": DESKTOP_CHROME}

# Every value the property has. Unknown is the one the cloud gives when it
# has too little to rate the request.
LEVELS = ("High", "Medium", "Low", "Unknown")

# The variable holding a resource key of the Basic product.
BASIC_KEY_NAME = "_51DEGREES_RESOURCE_KEY_BASIC"

# The properties the passive tests name in their request, so the answer
# carries both whatever the key's own list of properties holds.
PROPERTIES = "derived.humanconfidence,derived.humanconfidencesource"


@pytest.fixture(scope="module")
def key():
    resource_key = find_resource_key()
    if not resource_key:
        pytest.skip(
            f"{', '.join(RESOURCE_KEY_NAMES)} is not set. Set it to a "
            "resource key that carries HumanConfidence to run the Human "
            "Confidence cloud tests.")
    return resource_key


@pytest.fixture(scope="module")
def api():
    return example.api_base(ExampleUtils.get_cloud_endpoint())


@pytest.fixture
def naming_the_properties(monkeypatch):
    """Adds the properties to each request the example makes for the
    passive level, and leaves its evidence as it is."""

    real = requests.request

    def request(method, url, data=None, **kwargs):
        # The cloud request engine adds "?" to the address it posts to.
        if method == "POST" and url.split("?")[0].endswith(".json"):
            data = dict(data or {}, values=PROPERTIES)
        return real(method, url, data=data, **kwargs)

    monkeypatch.setattr(requests, "request", request)


@pytest.fixture(scope="module")
def client(key, api):
    if not example.carries_human_confidence(api, key):
        pytest.skip(
            "The resource key does not carry HumanConfidence, so the Human "
            "Confidence cloud tests cannot run with it.")
    return example.create_app(
        key, ExampleUtils.get_license_key(), api).test_client()


def test_page_is_served_and_never_kept(client, key):
    response = client.get("/", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert key in response.get_data(as_text=True)


def test_passive_level_comes_from_the_cloud(client, key, api,
                                           naming_the_properties):
    answer = client.get("/passive", headers=HEADERS).get_json()
    assert "error" not in answer, "The cloud refused the request."
    assert answer["humanConfidence"] in LEVELS
    assert answer["sent"]["url"] == api + key + ".json"


def test_a_basic_key_gets_a_passive_level(api, naming_the_properties,
                                         capsys):
    """The Basic product does not offer HumanConfidenceSource. When the
    cloud says its key carries HumanConfidence, the passive call gives a
    level. When it says the key does not, the example ends at start with
    the contact link, as a user running it with that key sees."""
    basic = read_environment(BASIC_KEY_NAME)
    if not basic:
        pytest.skip(
            f"{BASIC_KEY_NAME} is not set. Set the variable to a Resource "
            "Key of the Basic product to check the passive call with it.")
    if example.carries_human_confidence(api, basic):
        client = example.create_app(basic, None, api).test_client()
        answer = client.get("/passive", headers=HEADERS).get_json()
        assert "error" not in answer, "The cloud refused the request."
        assert answer["humanConfidence"] in LEVELS
    else:
        with pytest.raises(SystemExit) as stopped:
            example.main([basic])
        assert stopped.value.code == 1
        printed = capsys.readouterr().out
        assert "Contact us: https://51degrees.com/contact-us" in printed


def test_license_key_never_reaches_the_browser(client):
    license_key = ExampleUtils.get_license_key()
    if not license_key:
        pytest.skip(
            f"{ExampleUtils.LICENSE_KEY_ENV_VAR} is not set, so there is no "
            "License Key to look for.")
    for response in (client.get("/?mode=client", headers=HEADERS),
                     client.get("/?mode=server", headers=HEADERS),
                     client.get("/passive", headers=HEADERS),
                     client.post("/redeem", data={"value": "not-sealed"})):
        assert license_key.encode() not in response.data

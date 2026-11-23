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

The passive tests check that HumanConfidenceSource comes back. The Pro and
Bespoke products offer it, and the Bespoke key gets Passive, as no browser
tests have run. The Basic product does not offer HumanConfidenceSource, so
a Basic key gets no source.

The production cloud does not serve HumanConfidenceSource yet, so the two
tests that check it are marked staging and call the staging cloud that
CLOUD_STAGING_ENDPOINT names, with the Bespoke key in
RESOURCE_KEY_BESPOKE_STAGING and the Basic key in
_51DEGREES_RESOURCE_KEY_BASIC. Only the Cloud Human Confidence workflow sets
the two staging names, and without them these tests skip. The other tests
call the cloud _51DEGREES_CLOUD_ENDPOINT names.

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

# The variable holding the staging cloud's API base, ending /api/v4/. Only
# CI sets it, and there is no default, so a staging test never calls the
# production cloud.
STAGING_ENDPOINT_NAME = "CLOUD_STAGING_ENDPOINT"

# The variable holding a Bespoke resource key the staging cloud knows.
STAGING_KEY_NAME = "RESOURCE_KEY_BESPOKE_STAGING"

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
        if method == "POST" and url.endswith(".json"):
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


@pytest.fixture(scope="module")
def staging_api():
    endpoint = read_environment(STAGING_ENDPOINT_NAME)
    if not endpoint:
        pytest.skip(
            f"{STAGING_ENDPOINT_NAME} is not set. Set it to the staging "
            "cloud's API base to run the tests the production cloud cannot "
            "answer yet.")
    return example.api_base(endpoint)


@pytest.fixture(scope="module")
def staging_client(staging_api):
    staging_key = read_environment(STAGING_KEY_NAME)
    if not staging_key:
        pytest.skip(
            f"{STAGING_KEY_NAME} is not set. Set it to a Bespoke resource "
            "key the staging cloud knows.")
    if not example.carries_human_confidence(staging_api, staging_key):
        pytest.skip(
            f"The key in {STAGING_KEY_NAME} does not carry HumanConfidence "
            "on the staging cloud.")
    # The passive step never uses the License Key.
    return example.create_app(staging_key, None, staging_api).test_client()


def test_page_is_served_and_never_kept(client, key):
    response = client.get("/", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert key in response.get_data(as_text=True)


@pytest.mark.staging
def test_passive_source_and_level_come_from_the_cloud(
        staging_client, naming_the_properties):
    answer = staging_client.get("/passive", headers=HEADERS).get_json()
    assert "error" not in answer, answer
    assert answer["source"] == "Passive", answer
    assert answer["humanConfidence"] in LEVELS


@pytest.mark.staging
def test_a_basic_key_gets_no_source(staging_api, naming_the_properties):
    """The Basic product does not offer HumanConfidenceSource."""
    basic = read_environment(BASIC_KEY_NAME)
    if not basic:
        pytest.skip(
            f"{BASIC_KEY_NAME} is not set. The Basic product does not offer "
            "HumanConfidenceSource. Set the variable to a Basic resource "
            "key to check that such a key gets no source.")
    client = example.create_app(basic, None, staging_api).test_client()
    answer = client.get("/passive", headers=HEADERS).get_json()
    assert "error" not in answer, "The cloud refused the request."
    assert answer["source"] is None, answer


def test_licence_key_never_reaches_the_browser(client):
    licence_key = ExampleUtils.get_license_key()
    if not licence_key:
        pytest.skip(
            f"{ExampleUtils.LICENSE_KEY_ENV_VAR} is not set, so there is no "
            "licence key to look for.")
    for response in (client.get("/", headers=HEADERS),
                     client.get("/passive", headers=HEADERS)):
        assert licence_key.encode() not in response.data

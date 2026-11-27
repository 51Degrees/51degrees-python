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

## @example cloud/humanconfidence_web/app.py
#
# Human Confidence demo server. A Flask web application. Run:
# ```
# python -m fiftyone_pipeline_examples.cloud.humanconfidence_web
# ```
# then open http://localhost:5151/
#
# Human Confidence says how likely it is that a person is looking at the
# page. It comes in two ways, and this demo shows both.
#
# 1. Passive. This server asks the cloud itself, sending the visitor's
#    request headers and IP address. HumanConfidenceSource is Passive and
#    HumanConfidence is a plain level.
#    The server asks for it rather than reading it from the page, because
#    a level a browser sends can be forged.
# 2. Active. The page loads the 51Degrees client script, which runs the
#    browser tests and sends the answers to the cloud. When the script
#    completes, HumanConfidenceSource is Active and HumanConfidence holds
#    a sealed value the browser can't read or change.
# 3. Redeem. The page hands the sealed value to this server, which calls
#    hc/redeem with it and the account's License Key, and gets the true
#    level back. A sealed value redeems once, within ten seconds. This
#    server is the only party holding the License Key, which the browser
#    never sees.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/pipeline/fiftyone_pipeline_cloudrequestengine/examples/src/fiftyone_pipeline_examples/cloud/humanconfidence_web/app.py).
#
# Environment variables:
# - _51DEGREES_RESOURCE_KEY, the Resource Key, required
# - _51DEGREES_LICENSE_KEY, a License Key of the same account, required
#   to redeem
# - _51DEGREES_CLOUD_ENDPOINT, the API base including the /api/v4/
#   segment, defaults to https://cloud.51degrees.com/api/v4/
# - _51DEGREES_EXAMPLE_HTTP_PORTS, the port to listen on, defaults to 5151
#
# See readme.md beside this file for the steps and what to expect.
#
# Required PyPI dependencies:
# - [flask](https://pypi.org/project/flask/)
# - [requests](https://pypi.org/project/requests/)

import ipaddress
import os
import sys
import urllib.parse

import requests
from flask import Flask, Response, jsonify, make_response, render_template
from flask import request

from fiftyone_pipeline_examples.example_utils import ExampleUtils

DEFAULT_API = "https://cloud.51degrees.com/api/v4/"

# The property the Resource Key has to carry.
PROPERTY = "HumanConfidence"

# A short limit, in seconds, so a slow cloud can't hang the demo.
TIMEOUT = 10

# Where to go next. The page ends with these links, and the example prints
# them when it stops before the page is served.
FIND_OUT_MORE = [
    ("Bots and humans",
     "https://51degrees.com/bots-and-humans?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=find-out-more-bots-and-humans"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=find-out-more-resource-keys"),
    ("Pricing",
     "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=find-out-more-pricing"),
    ("Contact us",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=find-out-more-contact-us"),
    ("Pipeline API for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"),
]


def print_find_out_more():

    """!
    Print the "Find out more" section, a line of "=" and then each label
    with its link, to standard output. The example prints it when it stops
    before the page is served, which ends with the same links.
    """

    message = ["=" * 79, "Find out more:"]
    for label, url in FIND_OUT_MORE:
        message.append(f"\t{label}: {url}")
    print("\n".join(message) + "\n")


def api_base(endpoint):

    """!
    The cloud API base ending in /api/v4/, being the endpoint named, or the
    public cloud when none is named.
    """

    endpoint = (endpoint or "").strip()
    return (endpoint or DEFAULT_API).rstrip("/") + "/"


def carries_human_confidence(api, resource_key):

    """!
    Whether the Resource Key carries HumanConfidence, from the cloud's own
    list of the properties the key carries.
    """

    answer = requests.request(
        "GET",
        api + "accessibleproperties?resource=" +
        urllib.parse.quote(resource_key, safe=""),
        timeout=TIMEOUT)
    if answer.status_code != 200:
        raise ValueError(f"HTTP {answer.status_code}: {trim(answer.text)}")
    products = answer.json().get("Products") or {}
    for product in products.values():
        for item in (product or {}).get("Properties") or []:
            if str(item.get("Name", "")).lower() == PROPERTY.lower():
                return True
    return False


def create_app(resource_key, license_key, api):

    """!
    Create the Flask application that serves the page, asks the cloud for
    the passive level, and redeems the sealed active level.
    """

    # Serve the files in the static folder from the root, so the stylesheet
    # is at /css, as in the other web examples.
    app = Flask(__name__, static_url_path="")

    # The request headers the cloud reads, from its own list, fetched once.
    # Only these are passed on, so headers such as Authorization stay here.
    fetched = []

    def cloud_headers():
        if not fetched:
            answer = requests.request(
                "GET", api + "evidencekeys", timeout=TIMEOUT)
            if answer.status_code != 200:
                raise ValueError(
                    f"HTTP {answer.status_code}: {trim(answer.text)}")
            fetched.append({
                key[len("header."):].lower() for key in answer.json()
                if key.lower().startswith("header.")})
        return fetched[0]

    @app.route("/")
    def index():

        response = make_response(render_template(
            "index.html", resource_key=resource_key, api=api))
        # The page must never come from a cache, as each load runs the
        # tests.
        response.headers["Cache-Control"] = "no-store"
        return response

    # Passive: this server asks the cloud for the visitor, with the
    # visitor's headers and IP address, and reads the plain level from the
    # answer.
    @app.route("/passive")
    def passive():

        try:
            names = cloud_headers()
            evidence = {}
            for name, value in request.headers.items():
                if name.lower() in names:
                    evidence[name.lower()] = value
            # Behind a load balancer or CDN, use the visitor's address it
            # passes on. Set last, so no header can replace it.
            if request.remote_addr:
                evidence["client-ip"] = client_ip(request.remote_addr)
            answer = requests.request(
                "POST", api + resource_key + ".json", data=evidence,
                timeout=TIMEOUT)
            if answer.status_code >= 400:
                return jsonify(
                    error=f"HTTP {answer.status_code}: {trim(answer.text)}")
            derived = answer.json().get("derived")
            return jsonify(
                source=read(derived, "humanconfidencesource"),
                humanConfidence=read(derived, "humanconfidence"))
        except (requests.RequestException, ValueError) as error:
            return jsonify(error=str(error))

    # Redeem: the page sends the sealed value, and this server redeems it
    # with the License Key. The answer goes back to the page as the cloud
    # gave it.
    @app.route("/redeem", methods=["POST"])
    def redeem():

        fields = {"value": request.form.get("value", "")}
        if license_key:
            fields["license"] = license_key
        try:
            answer = requests.request(
                "POST", api + "hc/redeem", data=fields, timeout=TIMEOUT)
        except requests.RequestException as error:
            return jsonify(error=str(error)), 502
        if answer.status_code == 404:
            return jsonify(
                error=f"The service at {api} doesn't redeem Human "
                      "Confidence.")
        return Response(
            answer.text, status=answer.status_code,
            content_type="application/json")

    return app


def client_ip(address):

    """!
    The address of the connection, as IPv4 when it is an IPv4 address
    written as IPv6.
    """

    try:
        mapped = getattr(ipaddress.ip_address(address), "ipv4_mapped", None)
    except ValueError:
        return address
    return str(mapped) if mapped else address


def read(parent, name):

    """!
    The text held under name, or None when there is none.
    """

    value = parent.get(name) if isinstance(parent, dict) else None
    return value if isinstance(value, str) else None


def trim(text):
    return text[:200]


def main(argv):

    # A Resource Key given on the command line is used as it is. Otherwise
    # it comes from the environment.
    resource_key = argv[0] if len(argv) > 0 else \
        ExampleUtils.get_resource_key()
    if not resource_key.strip():
        print(f"Set {ExampleUtils.RESOURCE_KEY_ENV_VAR} to the Resource Key "
              "of the page. Resource keys are created at "
              "https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=resource-key-required")
        print_find_out_more()
        return

    license_key = ExampleUtils.get_license_key()
    api = api_base(ExampleUtils.get_cloud_endpoint())

    # Before the flow, ask the cloud whether the key carries
    # HumanConfidence, so a key without it is told so here.
    try:
        carried = carries_human_confidence(api, resource_key)
    except (requests.RequestException, ValueError) as error:
        print(error)
        print_find_out_more()
        sys.exit(1)
    if not carried:
        print("Contact us: "
              "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-humanconfidence_web-app.py&utm_term=human-confidence-required")
        print_find_out_more()
        sys.exit(1)

    if not license_key.strip():
        print(f"No {ExampleUtils.LICENSE_KEY_ENV_VAR} set. The page still "
              "shows Passive and Active, but an account that holds License "
              "Keys can't redeem without one, so the redeemed level will be "
              "unreadable.")

    app = create_app(resource_key, license_key, api)
    port = os.environ.get("_51DEGREES_EXAMPLE_HTTP_PORTS", 5151)
    print(f"Human Confidence demo on http://localhost:{port}/, using {api}")
    app.run(port=int(os.environ.get("_51DEGREES_EXAMPLE_HTTP_PORTS", 5151)))


if __name__ == "__main__":
    main(sys.argv[1:])

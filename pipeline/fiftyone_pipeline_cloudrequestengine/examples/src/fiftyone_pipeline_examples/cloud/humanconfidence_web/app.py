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
#    a sealed result the browser can't read or change. The package gives
#    each page its own script address, which binds the sealed result to
#    that page.
# 3. Read on the server. The page sends the sealed result back to this
#    server as humanconfidence. The server adds it to the evidence of a
#    pipeline holding the Cloud Request Engine, and reads the two
#    properties from flowdata.derived. The package redeems the sealed
#    result itself, with the License Key, so this server never redeems it
#    and the browser never sees the License Key. A sealed result redeems
#    once, so sending it again gives Medium.
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
import logging
import os
import sys
import threading
import urllib.parse

import requests
from flask import Flask, jsonify, make_response, render_template
from flask import request

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.humanconfidence import \
    DerivedCloud, HumanConfidenceTransactions
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_examples.example_utils import ExampleUtils

DEFAULT_API = "https://cloud.51degrees.com/api/v4/"

# The property the Resource Key has to carry.
PROPERTY = "HumanConfidence"

# A short limit, in seconds, so a slow cloud can't hang the demo.
TIMEOUT = 10

# What the page is told when the pipeline can't be built or a property
# can't be read. The details go to the server's log instead, because an
# error's text can name the License Key, which no page may receive.
BUILD_FAILED = "The pipeline could not be built. See the server's log."
READ_FAILED = "The property could not be read. See the server's log."

LOGGER = logging.getLogger(__name__)

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
    the passive level, and reads the active level through a pipeline,
    whose Cloud Request Engine redeems the sealed result.
    """

    # Serve the files in the static folder from the root, so the stylesheet
    # is at /css, as in the other web examples.
    app = Flask(__name__, static_url_path="")

    # Issues each page its transaction and keeps it here, on the server.
    transactions = HumanConfidenceTransactions()

    # The pipeline, built on first use, so the page is served without
    # asking the cloud anything.
    built = []
    building = threading.Lock()

    def pipeline():
        with building:
            if not built:
                settings = {
                    "resource_key": resource_key,
                    "cloud_endpoint": api,
                    "timeout_seconds": TIMEOUT,
                    "human_confidence_transactions": transactions}
                if license_key:
                    settings["license_key"] = license_key
                built.append(PipelineBuilder({
                    "add_javascript_builder": False,
                    "use_setheader_properties": False,
                    # A failed cloud request still gives the two
                    # properties, so it is recorded rather than raised.
                    "suppress_process_exceptions": True})
                    .add(CloudRequestEngine(settings))
                    .add(DerivedCloud())
                    .build())
        return built[0]

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

        # A new transaction for each page. The page loads the client script
        # from the address the package gives, and sends back the page id.
        page = transactions.issue()
        response = make_response(render_template(
            "index.html", script_url=page.script_url(api, resource_key),
            page_id=page.id))
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

    # Active: the page sends the sealed result and its page id. They go
    # into the evidence, and the two properties are read from the derived
    # data. The package redeems the sealed result while processing.
    @app.route("/humanconfidence", methods=["POST"])
    def human_confidence():

        try:
            flowdata = pipeline().create_flowdata()
        except Exception as error:
            LOGGER.error("Building the pipeline failed: %s",
                         hide(str(error), license_key))
            return jsonify(error=BUILD_FAILED)
        for name in ("humanconfidence", "humanconfidencepage"):
            flowdata.evidence.add(
                "query." + name, request.form.get(name, ""))
        flowdata.process()
        source, _ = property_of(flowdata, "humanconfidencesource")
        value, reason = property_of(flowdata, "humanconfidence")
        return jsonify(source=source, humanConfidence=value,
                       humanConfidenceNullReason=reason)

    return app


def property_of(flowdata, name):

    """!
    A property of the derived data as its value and the reason it has none,
    one of them None.
    """

    try:
        value = flowdata.derived.get(name)
    except Exception as error:
        LOGGER.error("Reading %s failed: %s", name, error)
        return None, READ_FAILED
    if value.has_value():
        return value.value(), None
    return None, value.no_value_message()


def hide(text, license_key):

    """!
    The text with the License Key left out, for the server's log.
    """

    return text.replace(license_key, "(hidden)") if license_key else text


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
              "shows Passive and Active, but the package redeems a sealed "
              "result only with one, so the level after the browser tests "
              "will be Medium.")

    app = create_app(resource_key, license_key, api)
    port = os.environ.get("_51DEGREES_EXAMPLE_HTTP_PORTS", 5151)
    print(f"Human Confidence demo on http://localhost:{port}/, using {api}")
    app.run(port=int(os.environ.get("_51DEGREES_EXAMPLE_HTTP_PORTS", 5151)))


if __name__ == "__main__":
    main(sys.argv[1:])

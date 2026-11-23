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
# page, as High, Medium or Low. The page shows it two ways.
#
# 1. Passive. This server asks the cloud with the visitor's request headers
#    and IP address, and gets a plain level.
# 2. Active. The 51Degrees client script runs the browser tests and sends
#    the answers to the cloud, which answers with a sealed value. This
#    server redeems the sealed value with the License Key, which the
#    browser never sees, and gets the level.
#
# The page works in two modes, chosen with ?mode=client or ?mode=server
# and kept in a cookie.
#
# - Client side. The browser loads the client script from the cloud and
#   the sealed value comes back to the page through fod.onChange.
# - Server side. The browser never calls the cloud. The page loads the
#   client script from this server, with every cloud address in it pointed
#   here, and this server sends each call on through the cloud request
#   engine.
#
# Under the results the page gives two curl commands that replay the
# passive call and the browser test answers from a terminal.
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
# Required PyPI dependencies:
# - [flask](https://pypi.org/project/flask/)
# - [requests](https://pypi.org/project/requests/)

import ipaddress
import json
import os
import re
import sys
import urllib.parse

import requests
from flask import Flask, Response, abort, jsonify, make_response
from flask import render_template, request

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from fiftyone_pipeline_examples.example_utils import ExampleUtils

DEFAULT_API = "https://cloud.51degrees.com/api/v4/"

# The property the Resource Key has to carry.
PROPERTY = "HumanConfidence"

# A short limit, in seconds, so a slow cloud can't hang the demo.
TIMEOUT = 10

# The two modes, the default first, and the cookie that keeps the choice.
MODES = ("client", "server")
MODE_COOKIE = "hc_mode"

# The levels, highest first. A level the cloud doesn't give is the last.
LEVELS = ("High", "Medium", "Low")

# The 51Degrees cloud hosts. The host of the endpoint in use, such as a
# private cloud in Docker, counts as a cloud host too.
CLOUD_HOSTS = r"cloud[a-z0-9-]*\.51degrees\.com"


def cloud_patterns(api):

    """!
    The cloud hosts for the endpoint api, and the cloud addresses in the
    client script, which in server mode are each pointed at this server.
    """

    hosts = CLOUD_HOSTS + "|" + re.escape(urllib.parse.urlsplit(api).netloc)
    return (re.compile(hosts),
            re.compile(r"(https?)://(" + hosts + r")/([^\"'\s\\)]*)"))

# Headers the cloud lists that are never sent on as HTTP headers, because
# they belong to this server's own connection to the cloud.
NOT_FORWARDED = {"host", "protocol", "client-ip", "content-length",
                 "content-type", "connection", "cookie"}

# The prefix, in lower case, of the cookies the client script and the cloud
# set.
COOKIE_PREFIX = "51d"

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
    the passive level, redeems the sealed active level, and in server mode
    sends the browser's calls on to the cloud.
    """

    # Serve the files in the static folder from the root, so the stylesheet
    # is at /css, as in the other web examples.
    app = Flask(__name__, static_url_path="")
    cloud_host, cloud_url = cloud_patterns(api)
    endpoint = urllib.parse.urlsplit(api)

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

    def visitor_headers():
        names = cloud_headers()
        return {name.lower(): value for name, value in request.headers.items()
                if name.lower() in names}

    # The cloud request engine, which sends this server's requests for data
    # to the cloud: the passive level, and in server mode the browser's
    # test answers. The page's own script is served by this server, so the
    # pipeline needs no JavaScript of its own.
    pipeline = PipelineBuilder({"add_javascript_builder": False}).add(
        CloudRequestEngine({"resource_key": resource_key,
                            "cloud_endpoint": api})).build()

    def ask_cloud(fields):
        """The cloud's answer for the visitor's headers and IP address and
        the form fields given, sent through the cloud request engine, with
        what was sent described for the page's curl command."""
        evidence = {"header." + name: value
                    for name, value in visitor_headers().items()}
        for name, value in fields:
            if name.lower() not in ("resource", "values"):
                evidence["query." + name] = value
        # Behind a load balancer or CDN, use the visitor's address it
        # passes on. Set last, so no header can replace it.
        address = public_ip(request.remote_addr)
        if address:
            evidence["query.client-ip"] = address
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
        if flowdata.errors:
            raise ValueError("; ".join(
                str(error) for error in flowdata.errors.values()))
        answer = flowdata.get("cloud").get("cloud")
        if isinstance(answer, str):
            answer = json.loads(answer)
        sent = {
            "method": "POST",
            "url": api + resource_key + ".json",
            "form": [[key.split(".", 1)[1], value]
                     for key, value in evidence.items()]}
        return answer, sent

    @app.route("/")
    def index():

        mode = request.args.get("mode")
        if mode not in MODES:
            mode = request.cookies.get(MODE_COOKIE)
        if mode not in MODES:
            mode = MODES[0]
        response = make_response(render_template(
            "index.html", resource_key=resource_key, api=api, mode=mode))
        response.set_cookie(MODE_COOKIE, mode, samesite="Lax")
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
            answer, sent = ask_cloud([])
            derived = answer.get("derived")
            return jsonify(
                humanConfidence=read(derived, "humanconfidence"), sent=sent)
        except Exception as error:
            return jsonify(error=str(error))

    # Redeem: the page, or a terminal, sends a sealed value, and this server
    # redeems it with the License Key. Only the level goes back. A value
    # that doesn't redeem gives Low, as nothing then shows a person is
    # there. The cloud's own answer is logged here, never sent back.
    @app.route("/redeem", methods=["POST"])
    def redeem():

        sealed = request.form.get("value", "")
        fields = {"value": sealed}
        if license_key:
            fields["license"] = license_key
        level, outcome = None, None
        try:
            answer = requests.request(
                "POST", api + "hc/redeem", data=fields, timeout=TIMEOUT)
            body = answer.json()
            level = read(body, "humanConfidence")
            outcome = read(body, "result") or (
                "redeemed" if level else f"HTTP {answer.status_code}")
        except (requests.RequestException, ValueError) as error:
            outcome = type(error).__name__
        if level not in LEVELS:
            level = LEVELS[-1]
        print(f"redeem: {level} ({outcome})", flush=True)
        return jsonify(humanConfidence=level)

    # Server mode: the client script, fetched from the cloud for this
    # visitor, with every cloud address in it pointed at this server.
    @app.route("/hc/script.js")
    def script():

        try:
            query = {}
            address = public_ip(request.remote_addr)
            if address:
                query["client-ip"] = address
            answer = requests.request(
                "GET", api + resource_key + ".js", params=query,
                headers=passed_on(visitor_headers()), timeout=TIMEOUT)
        except (requests.RequestException, ValueError) as error:
            return Response(
                "console.log(" + repr(str(error)) + ");", status=502,
                content_type="application/javascript")
        here = request.host_url + "hc/cloud/"
        text = cloud_url.sub(
            lambda m: here + m.group(2) + "/" + m.group(3), answer.text)
        response = Response(
            text, status=answer.status_code,
            content_type="application/javascript")
        response.headers["Cache-Control"] = "no-store"
        return response

    # Server mode: a call the client script makes to the cloud. The test
    # answers (a POST) go through the cloud request engine. A GET is the
    # third-party cookie check, sent on with the visitor's headers and only
    # the cloud's own cookies. Only cloud hosts are reached.
    @app.route("/hc/cloud/<host>/<path:path>", methods=["GET", "POST"])
    def forward(host, path):

        if not cloud_host.fullmatch(host):
            abort(404)
        if request.method == "POST":
            try:
                answer, _ = ask_cloud(request.form.items(multi=True))
            except Exception as error:
                return jsonify(error=str(error)), 502
            response = jsonify(answer)
            response.headers["Cache-Control"] = "no-store"
            return response
        # The endpoint's own host keeps the endpoint's scheme, as a private
        # cloud may be plain http.
        scheme = endpoint.scheme if host == endpoint.netloc else "https"
        url = scheme + "://" + host + "/" + path
        headers = passed_on(visitor_headers())
        cookies = "; ".join(
            f"{name}={value}" for name, value in request.cookies.items()
            if name.lower().startswith(COOKIE_PREFIX))
        if cookies:
            headers["Cookie"] = cookies
        try:
            answer = requests.request(
                "GET", url, params=request.args, headers=headers,
                timeout=TIMEOUT)
        except requests.RequestException as error:
            return jsonify(error=str(error)), 502
        response = Response(
            answer.content, status=answer.status_code,
            content_type=answer.headers.get(
                "Content-Type", "application/json"))
        for cookie in set_cookies(answer):
            response.headers.add("Set-Cookie", cookie)
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


def passed_on(headers):

    """!
    The visitor's headers to send as HTTP headers, without the ones that
    belong to this server's own connection.
    """

    return {name: value for name, value in headers.items()
            if name.lower() not in NOT_FORWARDED}


def set_cookies(answer):

    """!
    The cloud's Set-Cookie headers, made to work on this server's own
    address by dropping the domain, Secure and SameSite=None.
    """

    raw = getattr(answer, "raw", None)
    values = []
    if raw is not None and hasattr(raw, "headers") and \
            hasattr(raw.headers, "getlist"):
        values = raw.headers.getlist("Set-Cookie")
    kept = []
    for value in values:
        parts = [part.strip() for part in value.split(";")]
        parts = [part for part in parts if part and not
                 part.lower().startswith("domain=") and
                 part.lower() not in ("secure", "samesite=none")]
        kept.append("; ".join(parts))
    return kept


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


def public_ip(address):

    """!
    The visitor's address when it is a public one, otherwise None. A local
    or private address means nothing to the cloud, which then reads this
    server's own public address, the visitor's too when both are on one
    network.
    """

    if not address:
        return None
    address = client_ip(address)
    try:
        return address if ipaddress.ip_address(address).is_global else None
    except ValueError:
        return None


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
              "Keys can't redeem without one, so Active will show Low.")

    app = create_app(resource_key, license_key, api)
    port = os.environ.get("_51DEGREES_EXAMPLE_HTTP_PORTS", 5151)
    print(f"Human Confidence demo on http://localhost:{port}/, using {api}")
    # Threaded, so the page's calls in server mode don't wait on each other.
    app.run(port=int(port), threaded=True)


if __name__ == "__main__":
    main(sys.argv[1:])

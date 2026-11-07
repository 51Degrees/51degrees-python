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

"""The cache headers of the client-side JavaScript and JSON responses, as
the cache header detail of the web integration specification sets them."""

import os
import subprocess
import sys
from types import MappingProxyType
import unittest
from unittest import mock

from flask import Flask, request

from fiftyone_pipeline_core import web
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import javascript_response, json_response

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
SAFARI = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 "
          "Safari/605.1.15")

CACHEABLE = "max-age=1800, private"
NOT_CACHEABLE = "private, no-cache"


class Switchable(FlowElement):
    """An element that fails while failing is set, as a cloud request does
    while the service cannot be reached."""

    failing = False

    def __init__(self):
        super(Switchable, self).__init__()
        self.datakey = "switchable"
        self.properties = {"answer": {"type": "int"}}

    def process_internal(self, flowdata):
        if Switchable.failing:
            raise Exception("The stand-in service cannot be reached.")
        flowdata.set_element_data(ElementDataDictionary(self, {"answer": 42}))

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["header.user-agent"])


def client():
    """A test client of an application serving the two client-side
    endpoints."""

    pipeline = PipelineBuilder({
        "javascript_builder_settings": {"endpoint": "/json"},
        "suppress_process_exceptions": True,
    }).add(Switchable()).build()

    app = Flask(__name__)

    @app.route("/51Degrees.core.js")
    def javascript():
        return javascript_response(pipeline, request)

    @app.route("/json", methods=["POST"])
    def results():
        return json_response(pipeline, request)

    return app.test_client()


def script_etag():
    """The ETag of the JavaScript for a fixed request. Run in a process of
    its own by the test that compares processes."""

    return client().get(
        "/51Degrees.core.js", headers={"User-Agent": CHROME}).headers["ETag"]


class ClientSideCacheTests(unittest.TestCase):

    def setUp(self):
        Switchable.failing = False
        self.client = client()

    def tearDown(self):
        Switchable.failing = False

    def responses(self, headers):
        """The JavaScript and the JSON responses to the same evidence."""
        return [
            self.client.get("/51Degrees.core.js", headers=headers),
            self.client.post("/json", headers=headers),
        ]

    def test_a_good_response_may_be_kept_by_the_browser_alone(self):
        for response in self.responses({"User-Agent": CHROME}):
            self.assertEqual(200, response.status_code)
            self.assertEqual(CACHEABLE, response.headers.get("Cache-Control"))
            etag = response.headers.get("ETag")
            self.assertIsNotNone(etag, "a good response carries an ETag")
            self.assertTrue(etag.startswith('"') and etag.endswith('"'),
                            "an ETag is a quoted string: " + etag)
            self.assertIn("User-Agent", response.headers.get("Vary", ""))

    def test_the_content_type_says_which_endpoint_answered(self):
        script, results = self.responses({"User-Agent": CHROME})
        self.assertEqual("application/x-javascript",
                         script.headers["Content-Type"])
        self.assertEqual("application/json", results.headers["Content-Type"])
        self.assertIn(b"fiftyoneDegreesManager", script.data)
        self.assertEqual(42, results.get_json()["switchable"]["answer"])

    def test_the_etag_follows_the_evidence(self):
        first = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME})
        again = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME})
        other = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": SAFARI})
        self.assertEqual(first.headers["ETag"], again.headers["ETag"])
        self.assertNotEqual(first.headers["ETag"], other.headers["ETag"])

    def test_the_etag_is_the_same_in_every_process(self):
        """Python seeds the hash of a string afresh in each process, so the
        two processes are given different seeds."""

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from tests.test_web_client_side import script_etag; "
                "print(script_etag())")
        etags = []
        for seed in ("1", "2"):
            finished = subprocess.run(
                [sys.executable, "-c", code, root], capture_output=True,
                text=True, cwd=root, timeout=120,
                env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(0, finished.returncode, finished.stderr)
            etags.append(finished.stdout.strip().splitlines()[-1])
        self.assertEqual(etags[0], etags[1])
        self.assertEqual(script_etag(), etags[0])

    def test_revalidation_with_the_etag_is_answered_not_modified(self):
        good = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME})
        for method in (self.client.get, self.client.head):
            # A browser that revalidates sends Cache-Control as well when
            # the page is reloaded, and neither header is evidence.
            response = method("/51Degrees.core.js", headers={
                "User-Agent": CHROME,
                "If-None-Match": good.headers["ETag"],
                "Cache-Control": "max-age=0",
            })
            self.assertEqual(304, response.status_code)
            self.assertEqual(b"", response.data)
            # The headers of the good response that RFC 9110 section 15.4.5
            # asks a 304 to repeat.
            for name in ("ETag", "Cache-Control", "Vary"):
                self.assertEqual(good.headers.get(name),
                                 response.headers.get(name), name)

    def test_a_post_with_a_matching_etag_is_refused(self):
        """RFC 9110 section 13.1.2 allows a 304 for GET and HEAD only, and
        asks for 412 Precondition Failed for any other method."""

        etag = self.client.post(
            "/json", headers={"User-Agent": CHROME}).headers["ETag"]
        response = self.client.post("/json", headers={
            "User-Agent": CHROME, "If-None-Match": etag})
        self.assertEqual(412, response.status_code)
        self.assertEqual(b"", response.data)
        self.assertNotIn("ETag", response.headers)

    def test_the_web_request_value_is_not_in_the_etag(self):
        """The web integration may add the request itself as
        server.http-request, for the usage sharing element. It holds the
        request's every header, If-None-Match included, so it must not be
        hashed, even though the JavaScript builder accepts every key."""

        def with_web_request(request):
            evidence = webevidence(request)
            evidence["server.http-request"] = MappingProxyType(dict(evidence))
            return evidence

        webevidence = web.webevidence
        with mock.patch.object(web, "webevidence", with_web_request):
            etag = self.client.get(
                "/51Degrees.core.js", headers={"User-Agent": CHROME}) \
                .headers["ETag"]
            response = self.client.get("/51Degrees.core.js", headers={
                "User-Agent": CHROME, "If-None-Match": etag})
        self.assertEqual(304, response.status_code)

    def test_a_weak_or_listed_etag_still_matches(self):
        etag = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME}) \
            .headers["ETag"]
        for value in ("W/" + etag, '"other", ' + etag, "*"):
            response = self.client.get("/51Degrees.core.js", headers={
                "User-Agent": CHROME, "If-None-Match": value})
            self.assertEqual(304, response.status_code, value)
        response = self.client.get("/51Degrees.core.js", headers={
            "User-Agent": CHROME, "If-None-Match": '"other"'})
        self.assertEqual(200, response.status_code)

    def test_a_response_to_a_failed_request_carries_no_etag(self):
        Switchable.failing = True
        for response in self.responses({"User-Agent": CHROME}):
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                NOT_CACHEABLE, response.headers.get("Cache-Control"))
            self.assertNotIn("ETag", response.headers)

    def test_a_good_copy_is_kept_while_processing_fails(self):
        etag = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME}) \
            .headers["ETag"]
        Switchable.failing = True
        response = self.client.get("/51Degrees.core.js", headers={
            "User-Agent": CHROME, "If-None-Match": etag})
        self.assertEqual(304, response.status_code)

    def test_a_failed_response_is_replaced_once_processing_works(self):
        """The browser kept the failed response with no ETag, so it has
        nothing to revalidate with and asks again in full."""

        Switchable.failing = True
        failed = self.client.get(
            "/51Degrees.core.js", headers={"User-Agent": CHROME})
        Switchable.failing = False
        headers = {"User-Agent": CHROME}
        if "ETag" in failed.headers:
            headers["If-None-Match"] = failed.headers["ETag"]
        response = self.client.get("/51Degrees.core.js", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual(CACHEABLE, response.headers.get("Cache-Control"))


if __name__ == "__main__":
    unittest.main()

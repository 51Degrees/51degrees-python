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

"""The server route. A publisher's server serves the pipeline's JavaScript
to the browser, and the browser posts the answers of the scripts it ran
back to the server, which passes them on to the cloud through the Cloud
Request Engine. These tests follow that back and forth through a Flask
application, as a web integration serves it, and check what reaches the
cloud on each iteration: the session id, the sequence, the browser test
answers, and the visitor's IP address, JA4 and H2 that the server supplies
as query evidence."""

import re
import unittest
import warnings
from unittest import mock

from flask import Flask, request

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core import web
from fiftyone_pipeline_core.web import javascript_response, json_response
from fiftyone_pipeline_engines.basic_dictionary_cache import (
    BasicDictionaryCache)

from .classes.mockrequestclient import MockRequestClient

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# The visitor's connection as the server's TLS terminator saw it. The JA4
# is in the form the cloud captures. The H2 is the HTTP/2 SETTINGS text.
VISITOR_IP = "203.0.113.24"
VISITOR_JA4 = "t13d1516h2_8daaf6152771_02713d6af862"
VISITOR_H2 = "1:65536;2:0;4:6291456;6:262144|15663105|0|m,a,s,p"

# Browser test answers are sent under a name that starts 51D_ and changes
# with each script, and their value starts with a schema and a bar. Real
# answers are long, so one here is too.
ANSWER_NAME = "51D_k3Jq9xT"
ANSWER_VALUE = "3z|" + "aB0-_" * 12000
# A value a snippet stored as a cookie, which the script does not post.
COOKIE_NAME = "51D_Pos_m8Rt"
COOKIE_VALUE = "3|cookie-answer"

SESSION_ID = re.compile(r'var sessionId = "([^"]*)";')
SEQUENCE = re.compile(r"var sequence = ([0-9]+);")


def make_app(engine, supply_connection):
    """A Flask application serving the pipeline's JavaScript and the JSON
    endpoint the JavaScript posts to. Where supply_connection is set, the
    server adds the visitor's IP address, JA4 and H2 as query evidence, as
    a server behind a TLS terminator does."""

    pipeline = PipelineBuilder({
        "javascript_builder_settings": {
            "endpoint": "/json", "minify": False},
    }).add(engine).build()

    app = Flask(__name__)

    def evidence_of(req):
        evidence = original(req)
        if supply_connection:
            evidence["query.client-ip"] = VISITOR_IP
            evidence["query.ja4"] = VISITOR_JA4
            evidence["query.h2"] = VISITOR_H2
        return evidence

    # The web integration reads the request through webevidence, so the
    # server's own values are added by wrapping it while a request is
    # answered.
    original = web.webevidence

    @app.route("/51Degrees.core.js")
    def javascript():
        with mock.patch.object(web, "webevidence", evidence_of):
            return javascript_response(pipeline, request)

    @app.route("/json", methods=["POST"])
    def results():
        with mock.patch.object(web, "webevidence", evidence_of):
            return json_response(pipeline, request)

    return app.test_client()


class ServerRoutePassThroughTests(unittest.TestCase):

    def setUp(self):
        self.http = MockRequestClient()
        self.engine = CloudRequestEngine({
            "resource_key": "resource_key",
            "http_client": self.http,
        })

    def data_requests(self):
        """The body of every data request the engine made, in order."""
        return [content for (_, url, content) in self.http.requests
                if "resource_key.json" in url]

    def script_values(self, response):
        """The session id and the sequence the script was written with."""
        text = response.get_data(as_text=True)
        return (SESSION_ID.search(text).group(1),
                int(SEQUENCE.search(text).group(1)))

    def run_iterations(self, client):
        """The browser's side of the back and forth. It loads the script,
        then posts the session id and the sequence the script holds with
        its answers, twice, as a page does when a snippet's answers lead
        to another iteration."""

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            first = client.get("/51Degrees.core.js",
                               headers={"User-Agent": CHROME})
            self.assertEqual(200, first.status_code)
            session_id, sequence = self.script_values(first)
            client.set_cookie(COOKIE_NAME, COOKIE_VALUE)
            for _ in range(2):
                response = client.post("/json", headers={
                    "User-Agent": CHROME,
                }, data={
                    "session-id": session_id,
                    "sequence": str(sequence),
                    ANSWER_NAME: ANSWER_VALUE,
                })
                self.assertEqual(200, response.status_code)
                sequence += 1
        return session_id

    def test_session_id_sequence_and_answers_reach_the_cloud(self):
        """Every iteration sends the cloud the session id the script was
        written with, a sequence one more than the iteration before, and
        the answers the page posted and stored as cookies, unchanged."""

        session_id = self.run_iterations(make_app(self.engine, False))
        bodies = self.data_requests()
        self.assertEqual(3, len(bodies))

        sequences = [int(body["sequence"]) for body in bodies]
        self.assertEqual(
            [sequences[0], sequences[0] + 1, sequences[0] + 2], sequences)
        for body in bodies:
            self.assertEqual(session_id, body["session-id"])
            self.assertEqual(CHROME, body["user-agent"])
        for body in bodies[1:]:
            self.assertEqual(ANSWER_VALUE, body[ANSWER_NAME])
            self.assertEqual(COOKIE_VALUE, body[COOKIE_NAME])
        self.assertNotIn(ANSWER_NAME, bodies[0])

    def test_the_server_supplies_the_visitors_connection(self):
        """A server supplies the visitor's IP address, JA4 and H2 as query
        evidence, and the cloud gets them on every iteration under the
        names it reads, with the supplied address replacing the address
        the request arrived from."""

        self.run_iterations(make_app(self.engine, True))
        bodies = self.data_requests()
        self.assertEqual(3, len(bodies))
        for body in bodies:
            self.assertEqual(VISITOR_IP, body["client-ip"])
            self.assertEqual(VISITOR_JA4, body["ja4"])
            self.assertEqual(VISITOR_H2, body["h2"])

    def test_every_iteration_reaches_the_cloud_through_a_cache(self):
        """The cache key is made from the evidence keys the cloud lists,
        and the cloud lists none of the session id, the sequence, the
        answers, the JA4 or the H2. So two iterations of one page share a
        key, and without care the iteration carrying the answers would be
        answered from the cache and never reach the cloud."""

        self.engine.set_cache(BasicDictionaryCache())
        session_id = self.run_iterations(make_app(self.engine, True))
        bodies = self.data_requests()
        self.assertEqual(3, len(bodies))
        for body in bodies:
            self.assertEqual(session_id, body["session-id"])
            self.assertEqual(VISITOR_JA4, body["ja4"])
        for body in bodies[1:]:
            self.assertEqual(ANSWER_VALUE, body[ANSWER_NAME])

    def test_a_supplied_connection_is_never_served_from_a_cache(self):
        """A server call with no page iteration, but with the visitor's
        JA4 and H2, goes to the cloud each time, because the cloud judges
        the call on them and the cache key leaves them out."""

        self.engine.set_cache(BasicDictionaryCache())
        pipeline = PipelineBuilder({"add_javascript_builder": False}) \
            .add(self.engine).build()
        for ja4 in (VISITOR_JA4, "t13d1517h2_8daaf6152771_b1ff8ab2d16f"):
            data = pipeline.create_flowdata()
            data.evidence.add("header.user-agent", CHROME)
            data.evidence.add("query.ja4", ja4)
            data.evidence.add("query.h2", VISITOR_H2)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data.process()
        self.assertEqual(
            [VISITOR_JA4, "t13d1517h2_8daaf6152771_b1ff8ab2d16f"],
            [body["ja4"] for body in self.data_requests()])

    def test_any_other_call_is_still_served_from_a_cache(self):
        """A call that is neither a page iteration nor carries a supplied
        connection is cached as before."""

        self.engine.set_cache(BasicDictionaryCache())
        pipeline = PipelineBuilder({"add_javascript_builder": False}) \
            .add(self.engine).build()
        for _ in range(2):
            data = pipeline.create_flowdata()
            data.evidence.add("query.User-Agent", CHROME)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data.process()
        self.assertEqual(1, len(self.data_requests()))

    def test_without_supplied_values_the_connection_is_the_requests(self):
        """With nothing supplied, the address sent is the one the request
        arrived from, and no JA4 or H2 is sent."""

        self.run_iterations(make_app(self.engine, False))
        for body in self.data_requests():
            self.assertEqual("127.0.0.1", body["client-ip"])
            self.assertNotIn("ja4", body)
            self.assertNotIn("h2", body)


if __name__ == "__main__":
    unittest.main()

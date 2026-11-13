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

"""The evidence a pipeline's elements do not accept, and the web request the
web integration adds as server.http-request."""

import unittest

from flask import Flask, request, session

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence

from .classes.exampleflowelement1 import ExampleFlowElement1

# No JavaScript or set header elements, so the only filter is that of
# ExampleFlowElement1, which accepts header.user-agent.
NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}


class UnacceptedEvidenceTests(unittest.TestCase):

    def test_evidence_no_element_accepts_is_set_aside(self):
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add(ExampleFlowElement1()).build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a browser")
        flowdata.evidence.add("header.x-test", "set aside")
        flowdata.process()

        self.assertEqual(
            {"header.user-agent": "a browser"}, flowdata.evidence.get_all())
        self.assertEqual(
            {"header.x-test": "set aside"},
            flowdata.evidence.get_unaccepted())

    def test_the_web_request_is_added_and_set_aside(self):
        """No element reads server.http-request as evidence, even an element
        that accepts every key, as the JavaScript builder does."""

        pipeline = PipelineBuilder().add(ExampleFlowElement1()).build()
        app = Flask(__name__)
        with app.test_request_context(
                "/?campaign=a", headers={"User-Agent": "a browser",
                                         "X-Test": "a header"}):
            evidence = webevidence(request)
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add_from_dict(evidence)
        flowdata.process()

        self.assertNotIn("server.http-request", flowdata.evidence.get_all())
        view = flowdata.evidence.get_unaccepted()["server.http-request"]
        self.assertEqual("a header", view["header.x-test"])
        self.assertEqual("a browser", view["header.user-agent"])
        self.assertEqual("a", view["query.campaign"])
        # A read-only view of the request, not evidence an element can
        # change.
        with self.assertRaises(TypeError):
            view["header.x-test"] = "changed"

    def test_the_web_request_has_every_part_the_specification_names(self):
        app = Flask(__name__)
        app.secret_key = "a secret"
        with app.test_request_context(
                "/page?campaign=a",
                headers={"User-Agent": "a browser",
                         "Cookie": "sessionid=cookievalue"},
                environ_base={"REMOTE_ADDR": "203.0.113.5"}):
            session["51D_one"] = "first"
            session["theme"] = "dark"
            view = webevidence(request)["server.http-request"]

        self.assertEqual("a browser", view["header.user-agent"])
        self.assertEqual("cookievalue", view["cookie.sessionid"])
        self.assertEqual("a", view["query.campaign"])
        self.assertEqual("first", view["session.51D_one"])
        self.assertEqual("dark", view["session.theme"])
        self.assertEqual("203.0.113.5", view["server.client-ip"])
        self.assertEqual("http", view["header.protocol"])
        self.assertEqual("GET", view["server.request-method"])
        self.assertEqual("/page", view["server.request-path"])
        # The Cookie header carries every cookie, and cookies are their own
        # part of the view.
        self.assertNotIn("header.cookie", view)

    def test_session_numbers_and_booleans_are_added_as_text(self):
        """The on-premise engines take evidence values as text only, so a
        number or a boolean kept in the session must not reach them as
        anything else."""

        app = Flask(__name__)
        app.secret_key = "a secret"
        with app.test_request_context("/"):
            session["visits"] = 3
            session["ratio"] = 0.5
            session["consented"] = True
            session["basket"] = ["left", "out"]
            evidence = webevidence(request)

        view = evidence["server.http-request"]
        for source in (evidence, view):
            self.assertEqual("3", source["session.visits"])
            self.assertEqual("0.5", source["session.ratio"])
            self.assertEqual("True", source["session.consented"])
            self.assertNotIn("session.basket", source)


if __name__ == "__main__":
    unittest.main()

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

"""The request line the web integration hands over in server.http-request,
being the method, the path and the query string, each exactly as the
request line held them, as web-integration.md lines 100 to 114 ask."""

import unittest

from flask import Flask, request

from fiftyone_pipeline_core.web import webevidence


def view_of(path, **environ):
    """The request view webevidence gives for a request for the path, with
    the WSGI environment values given."""
    app = Flask(__name__)
    with app.test_request_context(path, environ_overrides=environ):
        return webevidence(request)["server.http-request"]


class RequestLineTests(unittest.TestCase):

    def test_all_three_values_are_given(self):
        view = view_of("/page?campaign=a")

        self.assertEqual("GET", view["server.request-method"])
        self.assertEqual("/page", view["server.request-path"])
        self.assertEqual("campaign=a", view["server.request-query"])

    def test_the_query_is_empty_when_there_is_none(self):
        view = view_of("/page")

        self.assertEqual("", view["server.request-query"])

    def test_the_values_are_as_the_request_line_held_them(self):
        view = view_of(
            "/a/b/~user", RAW_URI="/a%2Fb/%7Euser?b=2&a=%20one+two&a=3",
            QUERY_STRING="b=2&a=%20one+two&a=3")

        self.assertEqual("/a%2Fb/%7Euser", view["server.request-path"])
        self.assertEqual(
            "b=2&a=%20one+two&a=3", view["server.request-query"])

    def test_a_fragment_is_not_part_of_the_query(self):
        view = view_of("/page", RAW_URI="/page?a=1#part")

        self.assertEqual("a=1", view["server.request-query"])

    def test_the_query_string_is_taken_whole_with_no_request_line(self):
        # A server that does not say what the request line was gives the
        # query string undecoded, as WSGI does.
        view = view_of(
            "/page?b=2&a=%20one", RAW_URI="", REQUEST_URI="")

        self.assertEqual("b=2&a=%20one", view["server.request-query"])

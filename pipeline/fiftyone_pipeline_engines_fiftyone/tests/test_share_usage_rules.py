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
What usage sharing shares by default and when all Evidence is shared. A query
string or form parameter is shared only when its name starts with 51D_ or the
Pipeline uses it as evidence, whatever the settings, no cookie but a 51D_ one
is ever shared, and the session cookie is still compared when sessions are
tracked.
"""

import gzip
import json
import re
import unittest
from unittest import mock

import requests
from flask import Flask, request

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The package size is never reached, so the element keeps what it would
# share and sends nothing until it is closed.
QUEUE_ONLY = {
    "requested_package_size": 1000,
    "endpoint": "http://127.0.0.1:9",
}

# The deprecated option to share every query string parameter, from a
# configuration file.
CONFIGURATION = """
{
  "PipelineOptions": {
    "Elements": [
      {
        "elementName": "ShareUsage",
        "elementPath": "fiftyone_pipeline_engines_fiftyone.share_usage",
        "elementParameters": {
          "requested_package_size": 1000,
          "endpoint": "http://127.0.0.1:9",
          "share_all_query_string_parameters": false
        }
      }
    ]
  }
}
"""


def sent_on_close(usage):
    """Closes the element, which sends what it has queued, and returns each
    record it posted. The post is answered without leaving the process."""
    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


def records_of(usage, requests_evidence, *elements):
    """Processes each request's Evidence through a Pipeline holding the
    elements and the usage sharing element, and returns the records sent."""
    builder = PipelineBuilder(NO_DEFAULT_ELEMENTS)
    for element in elements:
        builder.add(element)
    pipeline = builder.add(usage).build()
    for evidence in requests_evidence:
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
    return sent_on_close(usage)


class UsingElement(FlowElement):
    """Accepts the query string parameter given as evidence, and adds no
    data."""

    def __init__(self, key):
        super(UsingElement, self).__init__()
        self.datakey = "using"
        self.key = key

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter([self.key])


# Every way the deprecated options could once share more.
DEPRECATED_SETTINGS = (
    {},
    {"share_all": True},
    {"query_whitelist": ["password", "campaign"]},
    {"share_all_query_string_parameters": True},
    {"share_all_query_string_parameters": False,
     "query_whitelist": "password,campaign"},
)


def shared_from_web_request(settings, method):
    """The record usage sharing sends for one web request with the
    parameters below, in its query string for GET or its form body for
    POST, through a Pipeline whose other element uses query.used."""
    app = Flask(__name__)
    usage = ShareUsage(**dict(QUEUE_ONLY, **settings))
    pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
        .add(UsingElement("query.used")).add(usage).build()
    parameters = {"51D_screen": "fiftyone value", "used": "used value",
                  "password": "password value", "campaign": "campaign value"}
    if method == "GET":
        context = app.test_request_context("/", query_string=parameters)
    else:
        context = app.test_request_context(
            "/", method="POST", data=parameters)
    with context:
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add_from_dict(webevidence(request))
        flowdata.process()
    records = sent_on_close(usage)
    return records[0] if records else ""


class QueryAndFormValuesTests(unittest.TestCase):

    def test_a_51d_parameter_is_shared_from_a_query_string_and_a_form(self):
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                record = shared_from_web_request({}, method)
                self.assertIn("fiftyone value", record)

    def test_a_parameter_the_pipeline_uses_is_shared_from_both(self):
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                record = shared_from_web_request({}, method)
                self.assertIn('<query Name="used">used value</query>', record)

    def test_no_other_parameter_is_ever_shared_from_either(self):
        for settings in DEPRECATED_SETTINGS:
            for method in ("GET", "POST"):
                with self.subTest(settings=settings, method=method):
                    record = shared_from_web_request(settings, method)
                    self.assertIn("fiftyone value", record)
                    self.assertNotIn("password value", record)
                    self.assertNotIn("campaign value", record)

    def test_the_javascript_builder_uses_only_the_parameters_it_lists(self):
        usage = ShareUsage(**QUEUE_ONLY)
        pipeline = PipelineBuilder().add(usage).build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "agent value")
        flowdata.evidence.add("query.password", "password value")
        flowdata.evidence.add("query.fod-js-object-name", "object value")
        flowdata.process()
        records = sent_on_close(usage)

        self.assertIn("agent value", records[0])
        self.assertIn("object value", records[0])
        self.assertNotIn("password value", records[0])

    def test_the_deprecated_option_from_a_configuration_file(self):
        pipeline = PipelineBuilder().build_from_configuration(
            json.loads(CONFIGURATION))
        usage = pipeline.get_element("shareusage")
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "agent value")
        flowdata.evidence.add("query.password", "password value")
        flowdata.process()
        records = sent_on_close(usage)

        self.assertFalse(usage.share_all_query_string_parameters)
        self.assertIn("agent value", records[0])
        self.assertNotIn("password value", records[0])

class CookieTests(unittest.TestCase):

    def test_only_51d_cookies_are_shared_when_all_evidence_is_shared(self):
        records = records_of(ShareUsage(share_all=True, **QUEUE_ONLY), [{
            "header.user-agent": "agent value",
            "cookie.51d_screenpixelswidth": "1080",
            "cookie.sessionid": "session value",
            "cookie._ga": "analytics value",
            "session.basket": "basket value",
        }])

        self.assertIn('<cookie Name="51d_screenpixelswidth">1080</cookie>',
                      records[0])
        self.assertNotIn("session value", records[0])
        self.assertNotIn("analytics value", records[0])
        # Sharing all Evidence still shares what it shared before, other
        # than cookies.
        self.assertIn("basket value", records[0])

    def test_the_session_cookie_is_compared_but_never_shared(self):
        for share_all in (False, True):
            with self.subTest(share_all=share_all):
                records = records_of(ShareUsage(
                    share_all=share_all, track_session=True,
                    cookie="sessionid", **QUEUE_ONLY), [
                        {"header.user-agent": "agent value",
                         "cookie.sessionid": "first session"},
                        {"header.user-agent": "agent value",
                         "cookie.sessionid": "first session"},
                        {"header.user-agent": "agent value",
                         "cookie.sessionid": "second session"},
                    ])

                # The repeat in the first session is not shared, and the
                # same Evidence from a new session is.
                self.assertEqual(2, len(records))
                for record in records:
                    self.assertNotIn("first session", record)
                    self.assertNotIn("second session", record)


if __name__ == "__main__":
    unittest.main()

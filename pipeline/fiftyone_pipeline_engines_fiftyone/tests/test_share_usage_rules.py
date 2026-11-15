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
What usage sharing shares by default and when all Evidence is shared, and
the packages each record names. Every query string and form parameter is
shared unless that is turned off, no cookie but a 51D_ one is ever shared,
the session cookie is still compared when sessions are tracked, and each
record names every 51Degrees package in use with its version.
"""

import gzip
import json
import re
import unittest
from importlib import metadata
from unittest import mock

import requests
from flask import Flask, request

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

# The packages a Pipeline holding only usage sharing uses, being the one
# holding the Pipeline, the one holding the element and the one that
# requires.
USAGE_SHARING_PACKAGES = (
    "fiftyone_pipeline_core",
    "fiftyone_pipeline_engines",
    "fiftyone_pipeline_engines_fiftyone",
)

# Turns off sharing every query string parameter, from a configuration
# file.
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


def canonical(name):
    """A package name as the package index compares names."""
    return re.sub(r"[-_.]+", "_", name).lower()


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


def packages_in(record):
    """The Package elements of a record, as name and version pairs."""
    return re.findall(r'<Package Name="([^"]*)">([^<]*)</Package>', record)


class StarSign(FlowElement):
    """An element from no installed package."""

    def __init__(self):
        super(StarSign, self).__init__()
        self.datakey = "starsign"

    def process_internal(self, flow_data):
        pass


class QueryAndFormValuesTests(unittest.TestCase):

    def test_every_query_value_is_shared_by_default(self):
        records = records_of(ShareUsage(**QUEUE_ONLY), [{
            "header.user-agent": "agent value",
            "query.campaign": "campaign value",
            "query.password": "password value",
        }])

        self.assertEqual(1, len(records))
        self.assertIn('<query Name="campaign">campaign value</query>',
                      records[0])
        self.assertIn('<query Name="password">password value</query>',
                      records[0])

    def test_every_form_value_of_the_web_request_is_shared_by_default(self):
        app = Flask(__name__)
        usage = ShareUsage(**QUEUE_ONLY)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        with app.test_request_context(
                "/", method="POST", data={"field": "form value"}):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add_from_dict(webevidence(request))
            flowdata.process()
        records = sent_on_close(usage)

        self.assertEqual(1, len(records))
        self.assertIn('<query Name="field">form value</query>', records[0])

    def test_turned_off_only_51d_and_listed_values_are_shared(self):
        records = records_of(ShareUsage(
            share_all_query_string_parameters=False,
            query_whitelist=["campaign"], **QUEUE_ONLY), [{
                "header.user-agent": "agent value",
                "query.campaign": "campaign value",
                "query.51d_gethighentropyvalues": "hev",
                "query.password": "password value",
            }])

        self.assertIn("campaign value", records[0])
        self.assertIn("hev", records[0])
        self.assertNotIn("password value", records[0])

    def test_turned_off_from_a_configuration_file(self):
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


class PackageTests(unittest.TestCase):

    def test_each_record_names_every_51degrees_package_in_use(self):
        records = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "first"},
            {"header.user-agent": "second"},
        ])

        self.assertEqual(2, len(records))
        for record in records:
            packages = packages_in(record)
            self.assertEqual(
                sorted(USAGE_SHARING_PACKAGES),
                sorted(canonical(name) for name, _ in packages))
            for name, version in packages:
                self.assertEqual(metadata.version(name), version, name)

    def test_packages_follow_the_flow_elements(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}])[0]

        self.assertRegex(
            record,
            r"</FlowElement>(<Package [^>]*>[^<]*</Package>)+<Language>")

    def test_an_element_from_no_package_names_no_package(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}], StarSign())[0]

        self.assertIn("<FlowElement>StarSign</FlowElement>", record)
        self.assertEqual(
            sorted(USAGE_SHARING_PACKAGES),
            sorted(canonical(name) for name, _ in packages_in(record)))

    def test_packages_that_are_not_51degrees_are_not_named(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}])[0]

        names = [canonical(name) for name, _ in packages_in(record)]
        for other in ("requests", "cachetools", "flask"):
            self.assertNotIn(other, names)


if __name__ == "__main__":
    unittest.main()

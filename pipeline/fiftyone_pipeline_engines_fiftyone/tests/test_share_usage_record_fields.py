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
The fields of each usage sharing record. The session id, the sequence and
the client IP are its SessionId, Sequence and ClientIP whatever the letters
of their keys, the record names the address of the server that made it, a
repeat in one session is shared once, and Evidence added beside the web
request, such as a TLS fingerprint or a billing key, reaches the message.
"""

import gzip
import re
import socket
import threading
import time
import unittest
from unittest import mock

import requests
from flask import Flask, request

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from fiftyone_pipeline_engines_fiftyone import share_usage
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

SERVER_IP = "192.0.2.1"

# How long a test waits for the element's lookup of the server's address.
LOOKUP_WAIT_SECONDS = 5

# Longer than processing one request takes on any runner, and far shorter
# than LOOKUP_WAIT_SECONDS, which a processing call that waited for the
# lookup would take.
PROCESS_SECONDS = 2

JA4 = "t13d1516h2_8daaf6152771_b0da82dd1658"
H2 = "1:65536;4:6291456|15663105|0|m,a,s,p"
RESOURCE_KEY = "AQS5HKcyAAAA"


def usage_element(**settings):
    """A usage sharing element that keeps what it would share, because its
    package size is never reached, and sends nothing until it is closed."""

    return ShareUsage(
        requested_package_size=1000, endpoint="http://127.0.0.1:9",
        **settings)


def sent_on_close(usage):
    """Closes the usage sharing element, which sends what it has queued,
    and returns each record it posted, in order. The post is answered with
    a 200 without leaving the process."""

    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


def found_by(addresses):
    """Stands in for socket.getaddrinfo, answering with the addresses."""

    def getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET6 if ":" in address else socket.AF_INET,
                 socket.SOCK_STREAM, 6, "", (address, 0))
                for address in addresses]
    return getaddrinfo


class ShareUsageRecordFieldsTests(unittest.TestCase):

    def test_session_id_and_sequence_are_recorded_whatever_their_case(self):
        # Evidence keys ignore letter case, so the session id, the sequence
        # and the client IP are the record's SessionId, Sequence and
        # ClientIP whatever the letters of their keys.
        usage = usage_element()
        self.addCleanup(usage.close)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        for session_key, sequence_key, ip_key in (
                ("query.session-id", "query.sequence", "server.client-ip"),
                ("query.Session-Id", "query.Sequence", "Server.Client-IP")):
            flow_data = pipeline.create_flowdata()
            flow_data.evidence.add("header.user-agent", "agent")
            flow_data.evidence.add(session_key, "the session")
            flow_data.evidence.add(sequence_key, "2")
            flow_data.evidence.add(ip_key, "203.0.113.7")
            data = usage.get_data_from_evidence(flow_data)
            self.assertEqual("the session", data.session_id, session_key)
            self.assertEqual(2, data.sequence, sequence_key)
            self.assertEqual("203.0.113.7", data.client_ip, ip_key)

    def test_the_record_names_the_server_ip(self):
        with mock.patch.object(share_usage, "host_address",
                               lambda: SERVER_IP):
            usage = usage_element()
            self.assertTrue(
                usage._server_ip_found.wait(LOOKUP_WAIT_SECONDS))
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        flow_data = pipeline.create_flowdata()
        flow_data.evidence.add("header.user-agent", "agent")
        flow_data.process()

        sent = sent_on_close(usage)

        self.assertEqual(1, len(sent))
        self.assertIn(
            "<ServerIP>" + SERVER_IP + "</ServerIP><Platform>", sent[0])

    def test_processing_does_not_wait_for_the_server_ip(self):
        # A slow name lookup leaves ServerIP empty until it ends, and the
        # records made after that carry the address.
        release = threading.Event()
        self.addCleanup(release.set)

        def slow():
            release.wait(LOOKUP_WAIT_SECONDS)
            return SERVER_IP

        with mock.patch.object(share_usage, "host_address", slow):
            usage = usage_element()
            pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
                .add(usage).build()
            start = time.monotonic()
            first = pipeline.create_flowdata()
            first.evidence.add("header.user-agent", "first")
            first.process()
            took = time.monotonic() - start
            release.set()
            self.assertTrue(
                usage._server_ip_found.wait(LOOKUP_WAIT_SECONDS))
        second = pipeline.create_flowdata()
        second.evidence.add("header.user-agent", "second")
        second.process()

        sent = sent_on_close(usage)

        self.assertLess(
            took, PROCESS_SECONDS, f"Processing took {took:.2f} seconds, "
            "so it waited for the lookup of the server's address.")
        self.assertEqual(2, len(sent))
        self.assertIn("<ServerIP></ServerIP>", sent[0])
        self.assertIn("<ServerIP>" + SERVER_IP + "</ServerIP>", sent[1])

    def test_the_server_ip_prefers_ipv4_and_leaves_out_loopback(self):
        for addresses, expected in (
                (["::1", "127.0.0.1", "2001:db8::5", "198.51.100.4"],
                 "198.51.100.4"),
                (["::1", "127.0.0.1", "2001:db8::5"], "2001:db8::5"),
                (["127.0.0.1", "::1"], ""),
                ([], "")):
            with mock.patch.object(socket, "getaddrinfo",
                                   found_by(addresses)):
                self.assertEqual(
                    expected, share_usage.host_address(), addresses)

    def test_the_server_ip_is_empty_when_the_lookup_fails(self):
        def fails(*args, **kwargs):
            raise socket.gaierror("no such host")

        with mock.patch.object(socket, "getaddrinfo", fails):
            self.assertEqual("", share_usage.host_address())

    def test_a_repeat_in_one_session_is_shared_once(self):
        # Three calls in one session, as a page and its script make them.
        # The second repeats the first's values with the next sequence, so
        # it is not shared. The third changes a 51D_ value, so it is shared
        # with the same session id and the sequence the Sequence Element
        # gave it.
        usage = usage_element()
        pipeline = PipelineBuilder().add(usage).build()
        values = {"header.user-agent": "agent",
                  "cookie.51D_ScreenPixelsWidth": "1080"}

        first = pipeline.create_flowdata()
        first.evidence.add_from_dict(values)
        first.process()
        session = first.evidence.get("query.session-id")
        self.assertTrue(session)

        second = pipeline.create_flowdata()
        second.evidence.add_from_dict(values)
        second.evidence.add("query.session-id", session)
        second.evidence.add("query.sequence", "1")
        second.process()

        third = pipeline.create_flowdata()
        third.evidence.add_from_dict(
            dict(values, **{"cookie.51D_ScreenPixelsWidth": "1440"}))
        third.evidence.add("query.session-id", session)
        third.evidence.add("query.sequence", "2")
        third.process()

        sent = sent_on_close(usage)

        self.assertEqual(
            ["1", "3"],
            [re.search(r"<Sequence>(\d+)</Sequence>", record).group(1)
             for record in sent], sent)
        for record in sent:
            self.assertIn("<SessionId>" + session + "</SessionId>", record)
        self.assertIn(">1080<", sent[0])
        self.assertIn(">1440<", sent[1])

    def test_evidence_added_beside_the_web_request_is_shared(self):
        # A TLS fingerprint, the HTTP/2 settings and a billing key, which a
        # proxy or the application adds beside the web request.
        usage = usage_element()
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        flow_data = pipeline.create_flowdata()
        with Flask(__name__).test_request_context(
                "/", headers={"User-Agent": "agent"}):
            flow_data.evidence.add_from_dict(webevidence(request))
        flow_data.evidence.add("server.ja4", JA4)
        flow_data.evidence.add("server.h2", H2)
        flow_data.evidence.add("fiftyone.resource-key", RESOURCE_KEY)
        flow_data.process()

        sent = sent_on_close(usage)

        self.assertEqual(1, len(sent))
        for name, value in (
                ("ja4", JA4), ("h2", H2), ("resource-key", RESOURCE_KEY)):
            self.assertRegex(
                sent[0],
                'Name="' + re.escape(name) + '"[^>]*>' + re.escape(value)
                + "<", name)
        self.assertIn('Name="user-agent"', sent[0])

    def test_a_repeat_with_keys_in_another_case_is_shared_once(self):
        # evidence.md line 10, "Keys MUST be case-insensitive", so the same
        # values under keys spelled in another case are a repeat.
        usage = usage_element()
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        for key in ("header.x-test", "Header.X-Test"):
            flow_data = pipeline.create_flowdata()
            flow_data.evidence.add("header.user-agent", "agent")
            flow_data.evidence.add(key, "the value")
            flow_data.process()
        self.assertEqual(1, len(sent_on_close(usage)))

    def test_evidence_is_recorded_under_its_prefix_in_lower_case(self):
        # The record names each value's element by the key's prefix, which
        # is the same element whatever the letters of the key.
        usage = usage_element()
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        flow_data = pipeline.create_flowdata()
        flow_data.evidence.add("Header.X-Test", "the value")
        flow_data.process()
        sent = sent_on_close(usage)
        self.assertEqual(1, len(sent))
        self.assertIn("<header ", sent[0])
        self.assertNotIn("<Header ", sent[0])
        self.assertIn(">the value<", sent[0])


if __name__ == "__main__":
    unittest.main()

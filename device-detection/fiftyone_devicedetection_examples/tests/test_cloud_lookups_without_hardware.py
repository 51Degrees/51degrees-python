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
Runs the TAC and native model lookup examples against a stand-in for the
cloud service, with a resource key that does not carry the hardware lookup.
Each example must say so in one line, with tagged links to create a key that
carries it and to contact us, and end normally without asking for a lookup.
When the stand-in fails the accessible properties request instead, each
example must end with that failure and never say the key lacks the lookup.
When the key carries the lookup and the lookup matches no device, each
example must say so under each heading and end normally. When the first
accessible properties request fails and the next succeeds, each example
must ask again and act on the answer it then gets. The stand-in
answers as the cloud service does, so these tests need no key and no
network.
"""

import http.server
import io
import json
import logging
import os
import threading
import unittest
import warnings
from contextlib import contextmanager, redirect_stdout
from unittest import mock

from fiftyone_pipeline_cloudrequestengine.cloudrequestexception import \
    CloudRequestException

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.cloud import nativemodellookup_console
from fiftyone_devicedetection_examples.cloud import taclookup_console

# The cloud service's answer to the accessible properties request for a
# resource key without the hardware lookup, cut down to one property.
ACCESSIBLE_PROPERTIES = {
    "Products": {
        "device": {
            "DataTier": "CloudV5Basic",
            "Properties": [
                {
                    "Name": "IsMobile",
                    "Type": "Boolean",
                    "Category": "Device",
                    "DelayExecution": False
                }
            ]
        }
    }
}

# The cloud service's answer to the accessible properties request for a
# resource key with the hardware lookup, cut down to Profiles with the three
# properties the examples print, and one device property.
ACCESSIBLE_PROPERTIES_WITH_HARDWARE = {
    "Products": {
        "device": {
            "DataTier": "CloudV5Bespoke",
            "Properties": [
                {
                    "Name": "IsMobile",
                    "Type": "Boolean",
                    "Category": "Device",
                    "DelayExecution": False
                }
            ]
        },
        "hardware": {
            "DataTier": "CloudV5Bespoke",
            "Properties": [
                {
                    "Name": "Profiles",
                    "Type": "Array",
                    "Category": "",
                    "ItemProperties": [
                        {
                            "Name": "HardwareVendor",
                            "Type": "String",
                            "Category": "Name",
                            "DelayExecution": False,
                            "EvidenceProperties": []
                        },
                        {
                            "Name": "HardwareModel",
                            "Type": "String",
                            "Category": "Name",
                            "DelayExecution": False,
                            "EvidenceProperties": []
                        },
                        {
                            "Name": "HardwareName",
                            "Type": "Array",
                            "Category": "Name",
                            "DelayExecution": False,
                            "EvidenceProperties": []
                        }
                    ],
                    "DelayExecution": False,
                    "EvidenceProperties": []
                }
            ]
        }
    }
}

# The cloud service's answer to a lookup that matches no device.
NO_DEVICES = {"hardware": {"profiles": []}}

# The values each example looks up.
TACS = ("35925406", "86386802")
NATIVE_MODELS = ("SC-03L", "iPhone11,8")

# Some of the evidence keys the cloud service accepts, with the TAC and the
# native model the examples look up.
EVIDENCE_KEYS = [
    "header.User-Agent",
    "query.User-Agent",
    "query.tac",
    "query.nativemodel"]

# Any resource key, as the stand-in does not check it.
RESOURCE_KEY = "stand-in-key"

# The start of each link the line gives, with the campaign tags every
# example's links carry.
CONFIGURE_LINK = (
    "https://51degrees.com/configure/QKyYH5XT?utm_source=code"
    "&utm_medium=example&utm_campaign=51degrees-python")
CONTACT_LINK = (
    "https://51degrees.com/contact-us?utm_source=code"
    "&utm_medium=example&utm_campaign=51degrees-python")

# The start of each heading a lookup prints.
LOOKUP_HEADING = "Which devices are associated"

# What the line printed in place of the lookups starts with.
NO_HARDWARE_LOOKUP = (
    "The resource key does not include HardwarePlatform.Profiles")

# The answer of a cloud service that is failing.
SERVER_ERROR = 500


def no_hardware_lookup(example):
    """The line the example prints in place of its lookups, with the tags of
    its own file."""
    tags = ("&utm_content=fiftyone_devicedetection_examples-src-"
            f"fiftyone_devicedetection_examples-cloud-{example}.py"
            "&utm_term=no-hardware-lookup")
    return (
        f"{NO_HARDWARE_LOOKUP}, the hardware lookup this example needs, so "
        "no devices are listed. "
        f"Create a resource key that includes it at {CONFIGURE_LINK}{tags}, "
        f"or contact us about it at {CONTACT_LINK}{tags}.")


class StandInHandler(http.server.BaseHTTPRequestHandler):
    """Answers the accessible properties and evidence keys requests as the
    cloud service does, with the server's accessible properties, and
    anything else with 404. The accessible properties request is answered
    with the server's failing status instead while it has failures left,
    and a lookup with the server's lookup answer when it has one. The method
    and path of each request are kept."""

    def do_GET(self):
        server = self.server
        server.requests.append(f"GET {self.path}")
        path = self.path.split("?", 1)[0].lower()
        if path.endswith("/accessibleproperties"):
            if server.failing and server.failures != 0:
                if server.failures is not None:
                    server.failures -= 1
                self.answer(server.failing,
                            {"errors": ["The service is failing."]})
            else:
                self.answer(200, server.accessible_properties)
        elif path.endswith("/evidencekeys"):
            self.answer(200, EVIDENCE_KEYS)
        else:
            self.answer(404, {"errors": ["Not found."]})

    def do_POST(self):
        self.server.requests.append(f"POST {self.path}")
        # The body is read before answering, so the client is not cut off
        # while it is still sending.
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        path = self.path.split("?", 1)[0].lower()
        if path.endswith(".json") and self.server.lookup is not None:
            self.answer(200, self.server.lookup)
        else:
            self.answer(404, {"errors": ["Not found."]})

    def answer(self, status, body):
        content = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass


@contextmanager
def stand_in_cloud(failing=None, failures=None,
                   accessible_properties=ACCESSIBLE_PROPERTIES, lookup=None):
    """A stand-in for the cloud service on a free port of this machine.
    failing is the status to answer the accessible properties request with,
    or None to answer it with accessible_properties. failures is how many
    of those requests fail, the first ones, or None for every one. lookup is
    the answer to each lookup request, or None to answer it with 404."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StandInHandler)
    server.requests = []
    server.failing = failing
    server.failures = failures
    server.accessible_properties = accessible_properties
    server.lookup = lookup
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


class Recorder(logging.Handler):
    """Keeps every record logged while it is attached."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def run_against(server, main):
    """Runs an example with the stand-in as its cloud service and a resource
    key in the environment, as a person runs it, and returns what it printed,
    the records it logged and the exception it ended with, or None when it
    ended normally. The warning the cloud request engine gives when a
    request fails while the pipeline is built is kept out of the test's
    output."""
    printed = io.StringIO()
    recorder = Recorder()
    root = logging.getLogger()
    root.addHandler(recorder)
    raised = None
    try:
        with mock.patch.dict(os.environ), redirect_stdout(printed), \
                warnings.catch_warnings(record=True):
            os.environ.pop(ExampleUtils.LICENSE_KEY_ENV_VAR, None)
            os.environ[ExampleUtils.RESOURCE_KEY_ENV_VAR] = RESOURCE_KEY
            os.environ[ExampleUtils.CLOUD_ENDPOINT_ENV_VAR] = (
                f"http://127.0.0.1:{server.server_address[1]}/api/v4/")
            try:
                main([])
            except Exception as error:
                raised = error
    finally:
        root.removeHandler(recorder)
    return printed.getvalue(), recorder.records, raised


def lookup_requests(server):
    """The lookup requests the stand-in received, each being a request for a
    .json resource."""
    return [request for request in server.requests if ".json" in request]


def accessible_properties_requests(server):
    """The accessible properties requests the stand-in received."""
    return [request for request in server.requests
            if "/accessibleproperties" in request.lower()]


class LookupsWithoutHardwareTests(unittest.TestCase):

    def assert_says_the_key_lacks_the_lookup(self, main, example, **cloud):
        """The key does not carry the lookup, so the example must say so in
        one line and end normally. cloud is given to stand_in_cloud, and the
        stand-in is returned for further checks."""
        with stand_in_cloud(**cloud) as server:
            printed, records, raised = run_against(server, main)

        self.assertIsNone(raised, printed)
        lines = printed.split("\n")
        self.assertIn(no_hardware_lookup(example), lines, printed)
        self.assertEqual(
            [], [line for line in lines if line.startswith(LOOKUP_HEADING)],
            printed)
        self.assertIn("Find out more:", printed)
        self.assertNotIn("Traceback", printed)
        self.assertEqual(
            [], [record.getMessage() for record in records
                 if record.levelno >= logging.ERROR])

        # The example decided from the stand-in's accessible properties, and
        # asked for no lookup, which is a request for a .json resource.
        self.assertTrue(
            accessible_properties_requests(server), server.requests)
        self.assertEqual([], lookup_requests(server))
        return server

    def assert_ends_with_the_failure(self, main):
        """A failed accessible properties request leaves the hardware
        engine with no properties, as a key without the lookup does, so the
        example must end with the failure rather than blame the key."""
        with stand_in_cloud(failing=SERVER_ERROR) as server:
            printed, _, raised = run_against(server, main)

        self.assertIsInstance(raised, CloudRequestException, printed)
        self.assertEqual(SERVER_ERROR, raised.httpStatusCode, printed)
        self.assertNotIn(NO_HARDWARE_LOOKUP, printed)
        self.assertNotIn(LOOKUP_HEADING, printed)
        self.assertEqual([], lookup_requests(server))

    def test_taclookup_console(self):
        self.assert_says_the_key_lacks_the_lookup(
            taclookup_console.main, "taclookup_console")

    def test_nativemodellookup_console(self):
        self.assert_says_the_key_lacks_the_lookup(
            nativemodellookup_console.main, "nativemodellookup_console")

    def test_taclookup_console_when_the_cloud_fails(self):
        self.assert_ends_with_the_failure(taclookup_console.main)

    def test_nativemodellookup_console_when_the_cloud_fails(self):
        self.assert_ends_with_the_failure(nativemodellookup_console.main)

    def assert_asks_again_after_one_failure(self, main, example):
        """The first accessible properties request fails and the next gives
        the answer for a key without the lookup, so the example must ask
        again and then say the key lacks the lookup."""
        server = self.assert_says_the_key_lacks_the_lookup(
            main, example, failing=SERVER_ERROR, failures=1)
        self.assertEqual(2, len(accessible_properties_requests(server)),
                         server.requests)

    def test_taclookup_console_when_the_cloud_fails_once(self):
        self.assert_asks_again_after_one_failure(
            taclookup_console.main, "taclookup_console")

    def test_nativemodellookup_console_when_the_cloud_fails_once(self):
        self.assert_asks_again_after_one_failure(
            nativemodellookup_console.main, "nativemodellookup_console")


class LookupsMatchingNoDeviceTests(unittest.TestCase):

    def assert_says_no_device_matches(self, main, kind, values, **cloud):
        """The key carries the lookup and each lookup matches no device, so
        under each value's heading the example must say so in one line.
        cloud is given to stand_in_cloud, and the stand-in is returned for
        further checks."""
        with stand_in_cloud(
                accessible_properties=ACCESSIBLE_PROPERTIES_WITH_HARDWARE,
                lookup=NO_DEVICES, **cloud) as server:
            printed, records, raised = run_against(server, main)

        self.assertIsNone(raised, printed)
        lines = printed.split("\n")
        for value in values:
            heading = f"Which devices are associated with the {kind} '{value}'?"
            self.assertIn(heading, lines, printed)
            self.assertEqual(
                f"\tNo devices are associated with this {kind}.",
                lines[lines.index(heading) + 1], printed)
        self.assertNotIn(NO_HARDWARE_LOOKUP, printed)
        self.assertIn("Find out more:", printed)
        self.assertNotIn("Traceback", printed)
        self.assertEqual(
            [], [record.getMessage() for record in records
                 if record.levelno >= logging.ERROR])
        self.assertEqual(len(values), len(lookup_requests(server)),
                         server.requests)
        return server

    def test_taclookup_console(self):
        self.assert_says_no_device_matches(
            taclookup_console.main, "TAC", TACS)

    def test_nativemodellookup_console(self):
        self.assert_says_no_device_matches(
            nativemodellookup_console.main, "native model name",
            NATIVE_MODELS)

    def assert_asks_again_after_one_failure(self, main, kind, values):
        """The first accessible properties request fails and the next gives
        the hardware lookup, so the example must ask again and run its
        lookups, rather than take the failure for a key without the
        lookup."""
        server = self.assert_says_no_device_matches(
            main, kind, values, failing=SERVER_ERROR, failures=1)
        self.assertEqual(2, len(accessible_properties_requests(server)),
                         server.requests)

    def test_taclookup_console_when_the_cloud_fails_once(self):
        self.assert_asks_again_after_one_failure(
            taclookup_console.main, "TAC", TACS)

    def test_nativemodellookup_console_when_the_cloud_fails_once(self):
        self.assert_asks_again_after_one_failure(
            nativemodellookup_console.main, "native model name",
            NATIVE_MODELS)


if __name__ == "__main__":
    unittest.main()

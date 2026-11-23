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
The stand-in answers as the cloud service does, so these tests need no key
and no network.
"""

import http.server
import io
import json
import logging
import os
import threading
import unittest
from contextlib import contextmanager, redirect_stdout
from unittest import mock

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


def no_hardware_lookup(example):
    """The line the example prints in place of its lookups, with the tags of
    its own file."""
    tags = ("&utm_content=fiftyone_devicedetection_examples-src-"
            f"fiftyone_devicedetection_examples-cloud-{example}.py"
            "&utm_term=no-hardware-lookup")
    return (
        "The resource key does not include HardwarePlatform.Profiles, the "
        "hardware lookup this example needs, so no devices are listed. "
        f"Create a resource key that includes it at {CONFIGURE_LINK}{tags}, "
        f"or contact us about it at {CONTACT_LINK}{tags}.")


class StandInHandler(http.server.BaseHTTPRequestHandler):
    """Answers the accessible properties and evidence keys requests as the
    cloud service does for a key without the hardware lookup, and anything
    else with 404. The method and path of each request are kept."""

    def do_GET(self):
        self.server.requests.append(f"GET {self.path}")
        path = self.path.split("?", 1)[0].lower()
        if path.endswith("/accessibleproperties"):
            self.answer(200, ACCESSIBLE_PROPERTIES)
        elif path.endswith("/evidencekeys"):
            self.answer(200, EVIDENCE_KEYS)
        else:
            self.answer(404, {"errors": ["Not found."]})

    def do_POST(self):
        self.server.requests.append(f"POST {self.path}")
        # The body is read before answering, so the client is not cut off
        # while it is still sending.
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
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
def stand_in_cloud():
    """A stand-in for the cloud service on a free port of this machine."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StandInHandler)
    server.requests = []
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
    key in the environment, as a person runs it, and returns what it printed
    and the records it logged."""
    printed = io.StringIO()
    recorder = Recorder()
    root = logging.getLogger()
    root.addHandler(recorder)
    try:
        with mock.patch.dict(os.environ), redirect_stdout(printed):
            os.environ.pop(ExampleUtils.LICENSE_KEY_ENV_VAR, None)
            os.environ[ExampleUtils.RESOURCE_KEY_ENV_VAR] = RESOURCE_KEY
            os.environ[ExampleUtils.CLOUD_ENDPOINT_ENV_VAR] = (
                f"http://127.0.0.1:{server.server_address[1]}/api/v4/")
            main([])
    finally:
        root.removeHandler(recorder)
    return printed.getvalue(), recorder.records


class LookupsWithoutHardwareTests(unittest.TestCase):

    def assert_says_the_key_lacks_the_lookup(self, main, example):
        with stand_in_cloud() as server:
            printed, records = run_against(server, main)

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
            any("/accessibleproperties" in request.lower()
                for request in server.requests), server.requests)
        self.assertEqual(
            [], [request for request in server.requests
                 if ".json" in request])

    def test_taclookup_console(self):
        self.assert_says_the_key_lacks_the_lookup(
            taclookup_console.main, "taclookup_console")

    def test_nativemodellookup_console(self):
        self.assert_says_the_key_lacks_the_lookup(
            nativemodellookup_console.main, "nativemodellookup_console")


if __name__ == "__main__":
    unittest.main()

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
Every request the Cloud Request Engine makes gives up when the cloud service
has not answered within the timeout, as the TimeoutSeconds option of the
cloud request engine specification says, so a service that accepts the
connection and never answers cannot hold the engine. The timeout is 2
seconds unless timeout_seconds gives another.
"""

import json
import socket
import threading
import warnings
from unittest import mock
from unittest.mock import Mock

import requests
from parameterized import parameterized

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.requestclient import RequestClient
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.constants import Constants

RESOURCE_KEY = "resource_key"

# The default timeout the specification gives, in seconds.
SPECIFICATION_TIMEOUT_SECONDS = 2

# A timeout other than the default, in seconds.
GIVEN_TIMEOUT_SECONDS = 7

# The shortest whole timeout, in seconds, so that the test of a service
# that never answers ends quickly.
SHORT_TIMEOUT_SECONDS = 1

# How long a test waits for a build that ends within a few seconds. It is
# only a guard, so that a build which never ends fails the test rather than
# holding it.
BUILD_GUARD_SECONDS = 120

# Part of the warning the engine gives when it is built without a
# discovery result, saying it will ask again.
RETRY_WARNING = "ask again when it is first used"

# Where a test sends a request when the address does not matter.
ANY_URL = "https://cloud.example/api/v4/evidencekeys"


def answer(text, url):
    """A response from the cloud service with the body given."""

    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.text = text
    response.content = text.encode("utf-8")
    response.json = lambda: json.loads(text)
    response.headers = {}
    response.url = url
    return response


class StandInService:
    """
    Stands in for requests.request. It answers as the cloud service does for
    a key that carries the device product, and keeps the keyword arguments
    of every request.
    """

    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if "accessibleProperties" in url:
            return answer(
                json.dumps(Constants.accessiblePropertiesResponse), url)
        if "evidencekeys" in url:
            return answer(Constants.evidenceKeysResponse, url)
        return answer(Constants.jsonResponse, url)

    def timeouts(self):
        """The timeout each request was given, or None for a request given
        none."""

        return [kwargs.get("timeout") for _, _, kwargs in self.calls]


def process(engine):
    """Process one request through a pipeline holding the engine."""

    pipeline = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False}).add(engine).build()
    data = pipeline.create_flowdata()
    data.evidence.add("query.User-Agent", Constants.userAgent)
    data.process()
    pipeline.close()
    return data


class TimeoutTests(CloudRequestEngineTestsBase):

    def serve(self):
        """Put the stand-in service in place of requests.request for this
        test, and give it."""

        service = StandInService()
        patcher = mock.patch.object(requests, "request", service.request)
        patcher.start()
        self.addCleanup(patcher.stop)
        return service

    def test_the_client_gives_requests_the_default_timeout(self):
        service = self.serve()

        RequestClient().request("GET", ANY_URL, None, None)

        self.assertEqual([SPECIFICATION_TIMEOUT_SECONDS], service.timeouts())

    def test_the_client_gives_requests_the_timeout_it_is_built_with(self):
        service = self.serve()

        RequestClient(GIVEN_TIMEOUT_SECONDS).request(
            "GET", ANY_URL, None, None)

        self.assertEqual([GIVEN_TIMEOUT_SECONDS], service.timeouts())

    def test_every_request_has_the_default_timeout(self):
        service = self.serve()

        process(CloudRequestEngine({"resource_key": RESOURCE_KEY}))

        # The two discovery requests and the request for data.
        self.assertEqual(
            [SPECIFICATION_TIMEOUT_SECONDS] * 3, service.timeouts())

    def test_a_timeout_of_none_is_the_default(self):
        service = self.serve()

        process(CloudRequestEngine({
            "resource_key": RESOURCE_KEY, "timeout_seconds": None}))

        self.assertEqual(
            [SPECIFICATION_TIMEOUT_SECONDS] * 3, service.timeouts())

    def test_every_request_has_the_timeout_given(self):
        service = self.serve()

        process(CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "timeout_seconds": GIVEN_TIMEOUT_SECONDS}))

        self.assertEqual([GIVEN_TIMEOUT_SECONDS] * 3, service.timeouts())

    def test_a_request_client_given_has_the_engines_timeout(self):
        service = self.serve()

        process(CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "http_client": RequestClient(),
            "timeout_seconds": GIVEN_TIMEOUT_SECONDS}))

        self.assertEqual([GIVEN_TIMEOUT_SECONDS] * 3, service.timeouts())

    def test_a_client_with_no_timeout_parameter_is_called_as_before(self):
        # The stand-in client's request method takes the four arguments an
        # older RequestClient took.
        client = self.mock_http()

        data = process(CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "http_client": client,
            "timeout_seconds": GIVEN_TIMEOUT_SECONDS}))

        self.assertEqual({}, data.errors)
        self.assertEqual(3, len(client.requests))

    def test_a_configuration_gives_the_timeout(self):
        service = self.serve()

        pipeline = PipelineBuilder().build_from_configuration({
            "PipelineOptions": {"Elements": [{
                "elementName": "CloudRequestEngine",
                "elementPath":
                    "fiftyone_pipeline_cloudrequestengine.cloudrequestengine",
                "elementParameters": {"settings": {
                    "resource_key": RESOURCE_KEY,
                    "timeout_seconds": GIVEN_TIMEOUT_SECONDS}}}]}})
        self.addCleanup(pipeline.close)
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", Constants.userAgent)
        data.process()

        self.assertEqual([GIVEN_TIMEOUT_SECONDS] * 3, service.timeouts())

    @parameterized.expand([
        ("zero", 0),
        ("negative", -1),
        ("text", "2"),
        ("true", True),
    ])
    def test_a_timeout_that_is_not_a_positive_number_is_refused(
            self, _, timeout_seconds):
        service = self.serve()

        with self.assertRaises(ValueError) as raised:
            CloudRequestEngine({
                "resource_key": RESOURCE_KEY,
                "timeout_seconds": timeout_seconds})

        self.assertIn("timeout_seconds", str(raised.exception))
        # The engine is refused before it asks the cloud service anything.
        self.assertEqual([], service.calls)

    def test_a_service_that_never_answers_does_not_hold_the_build(self):
        # The system completes each connection to a listening socket, and
        # nothing ever answers on it.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        endpoint = "http://127.0.0.1:{}/api/v4/".format(
            listener.getsockname()[1])
        built = {}

        def build():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                built["engine"] = CloudRequestEngine({
                    "resource_key": RESOURCE_KEY,
                    "cloud_endpoint": endpoint,
                    "timeout_seconds": SHORT_TIMEOUT_SECONDS})
            built["warnings"] = [str(warning.message) for warning in caught]

        builder = threading.Thread(target=build, daemon=True)
        builder.start()
        builder.join(BUILD_GUARD_SECONDS)

        self.assertFalse(
            builder.is_alive(),
            "The build is still waiting for a service that never answers.")
        self.assertIn("engine", built)
        retries = [
            message for message in built["warnings"]
            if RETRY_WARNING in message]
        self.assertEqual(1, len(retries), built["warnings"])

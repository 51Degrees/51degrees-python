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
The Cloud Request Engine asks the cloud service for the accessible
properties and the accepted evidence keys when it is built, as the start-up
activity of the cloud request engine specification says. An answer from 400
to 499 fails the build. A transient failure lets the build complete with a
warning, and the next use asks again. A Cloud Aspect Engine builds while
discovery is incomplete and takes its properties once discovery completes.
Each entry in the warnings list of an answer is given as a warning.
"""

import json
import warnings
from unittest.mock import Mock

import requests
from parameterized import parameterized

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestexception import \
    CloudRequestException
from fiftyone_pipeline_cloudrequestengine.requestclient import RequestClient
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.constants import Constants

# The endpoints, which the stand-in tells apart by the address.
PROPERTIES = "accessibleProperties"
EVIDENCE_KEYS = "evidencekeys"
DATA = "data"

RESOURCE_KEY = "resource_key"
LICENSE_KEY = "ABCDEFGHIJKL"
MASKED_LICENSE_KEY = "********IJKL"

# What the stand-in answers when it refuses a discovery request, in the
# form the cloud service uses.
REFUSAL = "58982060: resource_key not a valid resource key"
REFUSED = json.dumps({"errors": [REFUSAL]})

# What the stand-in answers when it fails, as a gateway in front of the
# service does, and as the service does itself.
UNAVAILABLE = "503 Service Unavailable"
FAILED = json.dumps({"errors": ["The service could not answer."]})

# Part of the warning the engine gives when it is built without a
# discovery result, saying it will ask again.
RETRY_WARNING = "ask again when it is first used"

# Part of the warning a Cloud Aspect Engine logs when the key does not
# carry its product.
MISSING_PRODUCT = "does not include access to any properties"


def answer(status, text, url):
    """A response from the cloud service."""

    response = Mock(spec=requests.Response)
    response.status_code = status
    response.text = text
    response.content = text.encode("utf-8")
    response.json = lambda: json.loads(text)
    response.headers = {}
    response.url = url
    return response


def answering(status, text):
    """A failure that answers with the status and the body given."""

    return lambda url: answer(status, text, url)


def raising(error_class):
    """A failure that raises as the requests library does when the service
    cannot be reached or does not answer in time."""

    def fail(url):
        raise error_class("The stand-in service did not answer " + url)

    return fail


class DiscoveryClient(RequestClient):
    """
    Stands in for the cloud service. An endpoint named in failures fails as
    the failure given says. Otherwise every endpoint answers as the cloud
    service does for a key that carries the device product. Every request
    is kept.
    """

    def __init__(self, data_response=Constants.jsonResponse):
        self.failures = {}
        self.data_response = data_response
        self.requests = []

    @staticmethod
    def endpoint(url):
        if PROPERTIES in url:
            return PROPERTIES
        if EVIDENCE_KEYS in url:
            return EVIDENCE_KEYS
        return DATA

    def count(self, endpoint):
        """How many requests the endpoint has received."""

        return len([
            request for request in self.requests
            if self.endpoint(request[1]) == endpoint])

    def request(self, method, url, content, origin):
        self.requests.append((method, url, content))
        endpoint = self.endpoint(url)
        failure = self.failures.get(endpoint)
        if failure is not None:
            return failure(url)
        if endpoint == PROPERTIES:
            return answer(
                200, json.dumps(Constants.accessiblePropertiesResponse), url)
        if endpoint == EVIDENCE_KEYS:
            return answer(200, Constants.evidenceKeysResponse, url)
        return answer(200, self.data_response, url)


class RecordingLogger(Logger):
    """Keeps every entry the pipeline logs, as level and message."""

    def __init__(self):
        super(RecordingLogger, self).__init__("debug")
        self.logged = []

    def log_internal(self, level, log):
        self.logged.append((level, log["message"]))

    def missing_product(self, datakey):
        return [
            entry for entry in self.logged
            if MISSING_PRODUCT in entry[1] and datakey in entry[1]]


def build(client, **settings):
    """A Cloud Request Engine on the resource key, using the client."""

    return CloudRequestEngine({
        "resource_key": RESOURCE_KEY,
        "http_client": client,
        **settings})


def build_recording_warnings(client):
    """Build an engine, and give it with the warnings given while it was
    built."""

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        engine = build(client)
    return engine, [str(warning.message) for warning in caught]


def build_quietly(client):
    """Build an engine, leaving out the warnings a failure gives."""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build(client)


def pipeline_for(*elements, suppress=False, logger=None):
    builder = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False,
        "suppress_process_exceptions": suppress})
    if logger is not None:
        builder.add_logger(logger)
    for element in elements:
        builder.add(element)
    return builder.build()


def process(pipeline):
    data = pipeline.create_flowdata()
    data.evidence.add("query.User-Agent", Constants.userAgent)
    data.process()
    return data


def cloud_engine(datakey):
    engine = CloudEngine()
    engine.datakey = datakey
    return engine


# Failures that may pass, each as a name and the failure of each endpoint.
TRANSIENT_FAILURES = [
    ("accessible_properties_500", {PROPERTIES: answering(500, FAILED)}),
    ("evidence_keys_503", {EVIDENCE_KEYS: answering(503, UNAVAILABLE)}),
    ("both_502", {
        PROPERTIES: answering(502, UNAVAILABLE),
        EVIDENCE_KEYS: answering(502, UNAVAILABLE)}),
    ("connection_failure", {
        PROPERTIES: raising(requests.exceptions.ConnectionError),
        EVIDENCE_KEYS: raising(requests.exceptions.ConnectionError)}),
    ("timeout", {
        PROPERTIES: raising(requests.exceptions.Timeout),
        EVIDENCE_KEYS: raising(requests.exceptions.Timeout)}),
]


class DiscoveryAtBuildTests(CloudRequestEngineTestsBase):

    def test_building_makes_both_discovery_requests(self):
        client = DiscoveryClient()
        engine = build(client)

        self.assertEqual(1, client.count(PROPERTIES))
        self.assertEqual(1, client.count(EVIDENCE_KEYS))
        self.assertEqual(0, client.count(DATA))

        # The results are kept, so reading them and processing ask for
        # neither again.
        self.assertIn("device", engine.flow_element_properties)
        self.assertEqual(["query.User-Agent"], engine.evidence_keys)
        data = process(pipeline_for(engine))
        self.assertEqual(
            Constants.jsonResponse, data.get("cloud").get("cloud"))
        self.assertEqual(1, client.count(PROPERTIES))
        self.assertEqual(1, client.count(EVIDENCE_KEYS))
        self.assertEqual(1, client.count(DATA))

    def test_a_licence_key_alone_makes_both_discovery_requests(self):
        client = DiscoveryClient()
        CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": ["device.value"],
            "http_client": client})

        self.assertEqual(1, client.count(PROPERTIES))
        self.assertEqual(1, client.count(EVIDENCE_KEYS))

    @parameterized.expand([
        ("accessible_properties_400", PROPERTIES, 400),
        ("accessible_properties_401", PROPERTIES, 401),
        ("accessible_properties_403", PROPERTIES, 403),
        ("evidence_keys_400", EVIDENCE_KEYS, 400),
        ("evidence_keys_401", EVIDENCE_KEYS, 401),
        ("evidence_keys_403", EVIDENCE_KEYS, 403),
    ])
    def test_a_refusal_fails_the_build(self, _, endpoint, status):
        client = DiscoveryClient()
        client.failures[endpoint] = answering(status, REFUSED)

        with self.assertRaises(CloudRequestException) as raised:
            build(client)

        self.assertEqual(status, raised.exception.httpStatusCode)
        self.assertIn(REFUSAL, raised.exception.message)
        # Both requests were made before the build failed.
        self.assertEqual(1, client.count(PROPERTIES))
        self.assertEqual(1, client.count(EVIDENCE_KEYS))

    def test_a_refusal_whose_body_is_not_json_fails_the_build(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(401, "Unauthorized")

        with self.assertRaises(CloudRequestException) as raised:
            build(client)

        self.assertEqual(401, raised.exception.httpStatusCode)
        self.assertIn("401", raised.exception.message)
        self.assertIn("Unauthorized", raised.exception.message)

    def test_a_refusal_fails_the_build_beside_a_transient_failure(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, UNAVAILABLE)
        client.failures[EVIDENCE_KEYS] = answering(403, REFUSED)

        with self.assertRaises(CloudRequestException) as raised:
            build(client)

        self.assertEqual(403, raised.exception.httpStatusCode)
        self.assertIn(REFUSAL, raised.exception.message)

    @parameterized.expand(TRANSIENT_FAILURES)
    def test_a_transient_failure_lets_the_build_complete(self, _, failures):
        client = DiscoveryClient()
        client.failures.update(failures)

        engine, messages = build_recording_warnings(client)

        self.assertIsNotNone(engine)
        self.assertEqual(1, client.count(PROPERTIES))
        self.assertEqual(1, client.count(EVIDENCE_KEYS))
        retries = [message for message in messages if RETRY_WARNING in message]
        self.assertEqual(1, len(retries), messages)

    @parameterized.expand(TRANSIENT_FAILURES)
    def test_the_next_use_retries_after_a_transient_failure(
            self, _, failures):
        client = DiscoveryClient()
        client.failures.update(failures)
        engine = build_quietly(client)
        pipeline = pipeline_for(engine)

        # The service answers again.
        client.failures.clear()
        data = process(pipeline)

        self.assertEqual({}, data.errors)
        self.assertEqual(
            Constants.jsonResponse, data.get("cloud").get("cloud"))
        # Each discovery request that failed was made once more, and each
        # one that succeeded was kept.
        for endpoint in (PROPERTIES, EVIDENCE_KEYS):
            expected = 2 if endpoint in failures else 1
            self.assertEqual(expected, client.count(endpoint), endpoint)
        self.assertIn("device", engine.flow_element_properties)
        self.assertEqual(["query.User-Agent"], engine.evidence_keys)

        # Nothing is fetched again on later requests.
        process(pipeline)
        for endpoint in (PROPERTIES, EVIDENCE_KEYS):
            expected = 2 if endpoint in failures else 1
            self.assertEqual(expected, client.count(endpoint), endpoint)

    def test_a_retry_that_fails_again_is_an_error_of_that_processing(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, UNAVAILABLE)
        client.failures[EVIDENCE_KEYS] = answering(503, UNAVAILABLE)

        with self.assertRaises(CloudRequestException) as raised:
            process(pipeline_for(build_quietly(client)))
        self.assertEqual(503, raised.exception.httpStatusCode)

        # suppress_process_exceptions applies, as to any other failure.
        data = process(pipeline_for(build_quietly(client), suppress=True))
        self.assertNotEqual({}, data.errors)


class CloudAspectEngineDiscoveryTests(CloudRequestEngineTestsBase):

    def test_an_aspect_engine_builds_while_discovery_has_failed(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, UNAVAILABLE)
        device = cloud_engine("device")
        logger = RecordingLogger()

        pipeline = pipeline_for(
            build_quietly(client), device, logger=logger)
        self.addCleanup(pipeline.close)

        # The metadata is absent for now, and the product is not said to
        # be missing, because that is not known yet.
        self.assertEqual({}, device.get_properties())
        self.assertEqual([], logger.missing_product("device"))

        # Once the service answers, the metadata is taken from the result,
        # rather than the empty one being kept.
        client.failures.clear()
        data = process(pipeline)

        self.assertEqual({}, data.errors)
        self.assertEqual(["value"], list(device.get_properties()))
        self.assertEqual(
            ["value"], list(pipeline.get_properties()["device"]))
        self.assertEqual(1, data.get("device").get("value").value())
        self.assertEqual([], logger.missing_product("device"))

    def test_a_missing_product_is_logged_once_discovery_completes(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, UNAVAILABLE)
        location = cloud_engine("location")
        logger = RecordingLogger()

        pipeline = pipeline_for(
            build_quietly(client), location, logger=logger)
        self.addCleanup(pipeline.close)
        self.assertEqual([], logger.missing_product("location"))

        client.failures.clear()
        for _ in range(3):
            data = process(pipeline)
            self.assertEqual({}, data.errors)

        self.assertEqual({}, location.get_properties())
        missing = logger.missing_product("location")
        self.assertEqual(1, len(missing), logger.logged)
        self.assertEqual("warning", missing[0][0])


class ResponseWarningsTests(CloudRequestEngineTestsBase):

    def process_recording_warnings(self, engine):
        """Process one request, and give the flow data with the warnings
        given while it was processed."""

        pipeline = pipeline_for(engine)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data = process(pipeline)
        return data, [str(warning.message) for warning in caught]

    def test_each_warning_in_an_answer_is_logged(self):
        first = "The first warning from the cloud service."
        second = "The second warning from the cloud service."
        response = json.dumps({
            "device": {"value": 1}, "warnings": [first, second]})

        data, messages = self.process_recording_warnings(
            build(DiscoveryClient(data_response=response)))

        # The warnings do not fail the request.
        self.assertEqual({}, data.errors)
        self.assertEqual(response, data.get("cloud").get("cloud"))
        for warning in (first, second):
            self.assertEqual(
                1, len([message for message in messages
                        if warning in message]), messages)

    def test_a_licence_key_in_a_warning_is_masked(self):
        response = json.dumps({
            "device": {"value": 1},
            "warnings": ["The licence key " + LICENSE_KEY + " expires soon."]})
        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": ["device.value"],
            "http_client": DiscoveryClient(data_response=response)})

        data, messages = self.process_recording_warnings(engine)

        self.assertEqual({}, data.errors)
        logged = "\n".join(messages)
        self.assertIn(MASKED_LICENSE_KEY, logged)
        self.assertNotIn(LICENSE_KEY, logged)

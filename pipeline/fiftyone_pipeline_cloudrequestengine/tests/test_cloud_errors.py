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

"""Each entry of the errors list the cloud service answers with is the text
of an error. One entry is the message of the exception raised, and several
are raised together, as one exception whose exceptions list holds one for
each entry, as cloud-request-engine.md lines 448 to 452 ask."""

import json
from unittest.mock import Mock

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestexception import \
    CloudRequestException
from fiftyone_pipeline_cloudrequestengine.constants import Constants

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

KEY = "ABCDEFGHIJKL"
MASKED = "************"


def answer(status, errors):
    text = json.dumps({"errors": errors})
    reply = Mock()
    reply.status_code = status
    reply.text = text
    reply.json = lambda: json.loads(text)
    reply.headers = {"x-test": "yes"}
    reply.url = "https://cloud.51degrees.com/api/v4/json"
    return reply


def error_text(entry):
    return "Error returned from 51Degrees cloud service: '" + entry + "'"


class CloudErrorsTests(CloudRequestEngineTestsBase):

    def engine(self):
        return CloudRequestEngine({
            "license_key": KEY,
            "requested_properties": ["device.ismobile"],
            "http_client": self.mock_http(),
        })

    def raised(self, status, errors):
        with self.assertRaises(CloudRequestException) as caught:
            self.engine().validate_response(answer(status, errors))
        return caught.exception

    def test_one_entry_is_the_message(self):
        exception = self.raised(400, ["The resource key is not valid."])

        self.assertEqual(
            error_text("The resource key is not valid."), exception.message)
        self.assertEqual(400, exception.httpStatusCode)
        self.assertEqual([], list(exception.exceptions))

    def test_several_entries_are_raised_together_one_for_each(self):
        exception = self.raised(400, ["First problem.", "Second problem."])

        self.assertEqual(
            Constants.EXCEPTION_CLOUD_ERRORS_MULTIPLE, exception.message)
        self.assertEqual(400, exception.httpStatusCode)
        self.assertEqual(
            [error_text("First problem."), error_text("Second problem.")],
            [inner.message for inner in exception.exceptions])
        for inner in exception.exceptions:
            self.assertIsInstance(inner, CloudRequestException)
            self.assertEqual(400, inner.httpStatusCode)
            self.assertEqual({"x-test": "yes"}, inner.responseHeaders)

    def test_the_text_of_the_exception_gives_each_entry(self):
        # A log or a traceback shows the text of the exception, so the text
        # of the one raised for several entries gives each of them.
        exception = self.raised(400, ["First problem.", "Second problem."])

        text = str(exception)

        self.assertIn(Constants.EXCEPTION_CLOUD_ERRORS_MULTIPLE, text)
        self.assertIn(error_text("First problem."), text)
        self.assertIn(error_text("Second problem."), text)

    def test_each_entry_shows_only_the_masked_key(self):
        exception = self.raised(400, [
            "The license key is not valid. License key(s): '" + KEY + "'",
            "Again '" + KEY + "'"])

        self.assertEqual(2, len(exception.exceptions))
        for inner in exception.exceptions:
            self.assertNotIn(KEY[:8], inner.message)
            self.assertIn(MASKED, inner.message)
        self.assertNotIn(KEY[:8], str(exception))


class SeveralErrorsInDiscoveryTests(CloudRequestEngineTestsBase):

    def test_the_retry_warning_gives_the_text_of_each_entry(self):
        from .test_discovery_at_build import (
            PROPERTIES, RETRY_WARNING, DiscoveryClient, answering,
            build_recording_warnings)
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, json.dumps(
            {"errors": ["First failure.", "Second failure."]}))

        _, messages = build_recording_warnings(client)

        retries = [m for m in messages if RETRY_WARNING in m]
        self.assertEqual(1, len(retries), messages)
        self.assertIn(error_text("First failure."), retries[0])
        self.assertIn(error_text("Second failure."), retries[0])

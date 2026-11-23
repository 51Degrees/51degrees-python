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

"""The cloud service names the licence key in the errors it answers with, and
the engine's exception shows only the key's last four characters."""

import json
from unittest.mock import Mock

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestexception import \
    CloudRequestException

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

KEY = "ABCDEFGHIJKL"
MASKED = "********IJKL"


def answer(status, text):
    reply = Mock()
    reply.status_code = status
    reply.text = text
    reply.json = lambda: json.loads(text)
    reply.headers = {}
    reply.url = "https://cloud.51degrees.com/api/v4/json"
    return reply


class LicenceKeyErrorTests(CloudRequestEngineTestsBase):

    def engine(self):
        return CloudRequestEngine({
            "license_key": KEY,
            "requested_properties": ["device.ismobile"],
            "http_client": self.mock_http(),
        })

    def test_the_errors_text_shows_only_the_masked_key(self):
        text = json.dumps({"errors": [
            "The license key is not valid. License key(s): '" + KEY + "'"]})
        with self.assertRaises(CloudRequestException) as caught:
            self.engine().validate_response(answer(400, text))
        self.assertNotIn(KEY[:8], str(caught.exception))
        self.assertIn(MASKED, str(caught.exception))

    def test_content_that_is_not_json_shows_only_the_masked_key(self):
        with self.assertRaises(CloudRequestException) as caught:
            self.engine().validate_response(
                answer(500, "Licence " + KEY + " refused"))
        self.assertNotIn(KEY[:8], str(caught.exception))
        self.assertIn(MASKED, str(caught.exception))

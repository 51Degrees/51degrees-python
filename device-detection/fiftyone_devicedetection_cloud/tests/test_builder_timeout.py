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

"""!
The Device Detection Cloud Pipeline Builder passes timeout_seconds to the
Cloud Request Engine, as it does the other cloud settings. These tests need
no network connection and no resource key.
"""

import unittest
import warnings

import requests

from fiftyone_pipeline_cloudrequestengine.requestclient import RequestClient

from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder

# A timeout other than the default, in seconds.
GIVEN_TIMEOUT_SECONDS = 7


class TimeoutRecorder(RequestClient):
    """!
    Stands in for the cloud service as it is when it cannot be reached, and
    keeps the timeout each request was given.
    """

    def __init__(self):
        self.timeouts = []

    def request(self, type, url, content, originHeader, timeout_seconds=None):
        self.timeouts.append(timeout_seconds)
        raise requests.exceptions.ConnectionError(
            "The stand-in service cannot be reached.")


class BuilderTimeoutTests(unittest.TestCase):

    def test_the_builder_passes_the_timeout_to_the_engine(self):
        recorder = TimeoutRecorder()

        # The service cannot be reached, which the engine gives as a
        # warning and builds regardless.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            DeviceDetectionCloudPipelineBuilder(
                resource_key="a-resource-key",
                timeout_seconds=GIVEN_TIMEOUT_SECONDS,
                http_client=recorder)

        # The two discovery requests made when the engine is built.
        self.assertEqual([GIVEN_TIMEOUT_SECONDS] * 2, recorder.timeouts)


if __name__ == "__main__":
    unittest.main()

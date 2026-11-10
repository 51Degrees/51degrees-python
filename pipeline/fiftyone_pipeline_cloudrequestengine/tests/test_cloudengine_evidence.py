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

"""A cloud engine reads only the cloud request engine's results, so it
accepts no evidence, and a cloud pipeline sends the service only the
evidence the service lists and the elements the builder adds read."""

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

LICENSE_KEY = "a-licence-key"
REQUESTED = ["device.ismobile", "device.istablet"]


class CloudEngineEvidenceTests(CloudRequestEngineTestsBase):

    def test_a_cloud_engine_accepts_no_evidence(self):
        engine = CloudEngine()
        for key in ("query.user-agent", "header.user-agent", "header.x-test",
                    "cookie.51d_profileids", "query.session-id",
                    "server.client-ip"):
            self.assertFalse(engine.filter_evidence_key(key), key)

    def test_a_cloud_pipeline_sends_only_the_evidence_the_service_lists(self):
        """
        The stand-in service lists query.User-Agent alone, so of this
        evidence only the user agent reaches it.
        """
        cloud = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })
        engine = CloudEngine()
        engine.datakey = "device"

        pipeline = PipelineBuilder().add(cloud).add(engine).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", "iPhone")
        data.evidence.add("header.x-test", "a header")
        data.evidence.add("cookie.other", "a cookie")
        data.process()

        request_type, url, content = cloud.http_client.requests[-1]
        self.assertEqual("iPhone", content["user-agent"])
        self.assertNotIn("x-test", content)
        self.assertNotIn("other", content)

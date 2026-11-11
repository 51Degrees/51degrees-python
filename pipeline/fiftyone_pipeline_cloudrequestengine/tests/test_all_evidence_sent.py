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

"""The Cloud Request Engine sends every Evidence value in the Flow Data,
apart from the reserved names and the web request view, as the Processing
section of cloud-request-engine.md says at e972d136."""

import warnings

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.constants import Constants
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

RESOURCE_KEY = "resource_key"
LICENSE_KEY = "a-licence-key"


class TestAllEvidenceSent(CloudRequestEngineTestsBase):
    """!
    A cloud-only pipeline, so the Cloud Request Engine is the only element
    and its accepted Evidence is the list the stand-in service gives, which
    holds query.User-Agent alone. Everything else is Evidence no element in
    the pipeline accepts, and the engine still sends it.
    """

    def send(self, evidence, settings=None):
        """
        Process one flow data holding the evidence given, through a
        pipeline whose only element is the Cloud Request Engine, and give
        back the body of the data request.
        """

        settings = dict(settings or {})
        settings.setdefault("resource_key", RESOURCE_KEY)
        settings["http_client"] = self.mock_http()
        engine = CloudRequestEngine(settings)
        pipeline = PipelineBuilder().add(engine).build()
        data = pipeline.create_flowdata()
        for key, value in evidence.items():
            data.evidence.add(key, value)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data.process()

        return engine.http_client.requests[-1][2]

    def test_evidence_the_service_does_not_list_is_sent(self):
        """
        The stand-in service lists none of these three names, so a store
        that keeps only the accepted Evidence loses all three before the
        engine reads them. The specification says the engine makes the
        request "with every Evidence value in the Flow Data, apart from the
        reserved names and the web request view".
        """

        content = self.send({
            "query.my-own-thing": "a value",
            "header.sec-ch-ua-platform": "Windows",
            "cookie.51D_experiment": "b",
        })

        self.assertEqual("a value", content["my-own-thing"])
        self.assertEqual("Windows", content["sec-ch-ua-platform"])
        # add_query_data lowercases the name it sends, which is how the
        # engine behaved before this change and is not part of it.
        self.assertEqual("b", content["51d_experiment"])

    def test_evidence_the_service_lists_is_still_sent(self):
        """
        An accepted key is still sent, so reading the set aside Evidence as
        well has not displaced the Evidence the engine sent before.
        """

        content = self.send({
            "query.User-Agent": "a browser",
            "query.my-own-thing": "a value",
        })

        self.assertEqual("a browser", content["user-agent"])
        self.assertEqual("a value", content["my-own-thing"])

    def test_query_evidence_wins_whether_listed_or_not(self):
        """
        Query evidence takes precedence over header and cookie evidence of
        the same name, whether the service lists the name or not.
        """

        content = self.send({
            "cookie.my-own-thing": "from the cookie",
            "header.my-own-thing": "from the header",
            "query.my-own-thing": "from the query",
        })

        self.assertEqual("from the query", content["my-own-thing"])

    def test_a_reserved_name_is_never_sent_from_evidence(self):
        """
        The service reads its credentials and the property list from these
        names, so Evidence carrying one of them would sit beside the
        engine's own values with no way to know which one the service
        applied. The specification says Evidence under any prefix whose key
        strips to values, resource, license or licence, in any letter case,
        MUST be left out.
        """

        content = self.send({
            "query.resource": "evidence_resource",
            "query.License": "evidence_license",
            "header.LICENCE": "evidence_licence",
            "cookie.values": "evidence_values",
            "query.my-own-thing": "a value",
        }, {
            "license_key": LICENSE_KEY,
            "requested_properties": ["device.ismobile"],
        })

        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertEqual(
            "device.ismobile", content[Constants.VALUES_PARAMETER])
        self.assertNotIn(Constants.LICENCE_SPELLING, content)
        for name, value in content.items():
            self.assertNotIn("evidence_", str(value), name)
        self.assertEqual("a value", content["my-own-thing"])

    def test_the_web_request_view_is_never_sent(self):
        """
        A web integration adds the web request itself under
        server.http-request. It is a view of the whole request and not a
        value to send, so the specification says it MUST be left out.
        """

        content = self.send({
            "server.http-request": {"headers": {"user-agent": "a browser"}},
            "query.my-own-thing": "a value",
        })

        self.assertEqual(
            [], [name for name in content if "http-request" in name.lower()])
        self.assertEqual("a value", content["my-own-thing"])

    def test_a_reserved_name_is_left_out_under_any_prefix_and_case(self):
        """
        The letter case of the key does not change which name the service
        reads, so a reserved name under any prefix is left out whatever its
        case.
        """

        content = self.send({
            "header.ReSoUrCe": "evidence_resource",
            "cookie.LiCeNsE": "evidence_license",
            "query.VALUES": "evidence_values",
        })

        for name, value in content.items():
            self.assertNotIn("evidence_", str(value), name)

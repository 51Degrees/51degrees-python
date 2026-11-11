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
        self.assertEqual("b", content["51D_experiment"])

    def test_evidence_the_service_lists_is_still_sent(self):
        """
        An accepted key is still sent, so reading the set aside Evidence as
        well has not displaced the Evidence the engine sent before.
        """

        content = self.send({
            "query.User-Agent": "a browser",
            "query.my-own-thing": "a value",
        })

        self.assertEqual("a browser", content["User-Agent"])
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

    def test_each_prefix_wins_over_every_later_one(self):
        """
        evidence.md lists query, header, cookie, server, fiftyone and
        location from highest to lowest precedence, and ranks any other
        prefix alphabetically after them. Each pair of prefixes gives one
        name, added higher first so the order added cannot decide it, and
        the higher prefix's value is the one sent.
        """

        order = ("query", "header", "cookie", "server", "fiftyone",
                 "location", "apple", "zebra")
        evidence = {}
        for i, higher in enumerate(order):
            for lower in order[i + 1:]:
                name = "n-" + higher + "-" + lower
                evidence[higher + "." + name] = higher
                evidence[lower + "." + name] = lower

        content = self.send(evidence)

        wrong = []
        for i, higher in enumerate(order):
            for lower in order[i + 1:]:
                name = "n-" + higher + "-" + lower
                if content.get(name) != higher:
                    wrong.append(name + " sent " + str(content.get(name)))
        self.assertEqual([], wrong)

    def test_a_prefix_ranks_the_same_in_any_letter_case(self):
        """
        Evidence keys ignore letter case, so Location ranks as location and
        SERVER as server.
        """

        content = self.send({
            "fiftyone.b": "fiftyone",
            "Location.b": "location",
            "SERVER.c": "server",
            "Location.c": "location",
        })

        self.assertEqual("fiftyone", content["b"])
        self.assertEqual("server", content["c"])

    def test_other_prefixes_rank_by_the_prefix_alone(self):
        """
        Other prefixes rank alphabetically by the prefix, so ab comes
        before ab-c, although the key ab-c.n sorts before ab.n because a
        hyphen sorts before a dot.
        """

        content = self.send({"ab.n": "ab", "ab-c.n": "ab-c"})

        self.assertEqual("ab", content["n"])

    def test_a_reserved_name_is_never_sent_from_evidence(self):
        """
        The service reads its credentials and the property list from these
        names, so Evidence carrying one of them would sit beside the
        engine's own values with no way to know which one the service
        applied. The specification says Evidence under any prefix whose key
        strips to values, resource, license or licence, in any letter case,
        MUST be left out.
        """

        evidence = {
            "query.resource": "evidence_resource",
            "query.License": "evidence_license",
            "header.LICENCE": "evidence_licence",
            "cookie.values": "evidence_values",
            "query.my-own-thing": "a value",
        }

        # A resource key and a licence key, with no property list, so
        # nothing the engine sends is called values.
        content = self.send(evidence, {"license_key": LICENSE_KEY})
        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertNotIn(Constants.VALUES_PARAMETER, content)
        self.assertNotIn(Constants.LICENCE_SPELLING, content)
        for name, value in content.items():
            self.assertNotIn("evidence_", str(value), name)
        self.assertEqual("a value", content["my-own-thing"])

        # A licence key alone, with the property list it needs, so nothing
        # the engine sends is called resource.
        content = self.send(evidence, {
            "resource_key": "",
            "license_key": LICENSE_KEY,
            "requested_properties": ["device.ismobile"],
        })
        self.assertNotIn(Constants.RESOURCE_PARAMETER, content)
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

    def test_the_name_sent_is_everything_after_the_first_dot(self):
        """
        The prefix is the text before the first dot, and removing it leaves
        the rest of the key, dots included. So a.license is not the
        reserved name license, and a key with no dot is sent whole.
        """

        content = self.send({
            "query.a.license": "after the first dot",
            "header.x.y.z": "three parts",
            "nodot": "no prefix",
        })

        self.assertEqual("after the first dot", content["a.license"])
        self.assertEqual("three parts", content["x.y.z"])
        self.assertEqual("no prefix", content["nodot"])
        self.assertNotIn("z", content)

    def test_the_name_sent_keeps_the_letter_case_given(self):
        """
        The name is sent in the letter case of the evidence key, as .NET
        sends it, rather than lower-cased.
        """

        content = self.send({
            "cookie.51D_Experiment": "b",
            "header.Sec-CH-UA-Platform": "Windows",
        })

        self.assertEqual("b", content["51D_Experiment"])
        self.assertEqual("Windows", content["Sec-CH-UA-Platform"])
        self.assertNotIn("51d_experiment", content)
        self.assertNotIn("sec-ch-ua-platform", content)

    def test_one_name_in_two_letter_cases_is_sent_once(self):
        """
        Evidence keys ignore letter case, so header.User-Agent and
        query.user-agent name the same value, and the query value wins
        under the precedence order. The name is sent once, spelled as the
        winning key spells it.
        """

        content = self.send({
            "header.User-Agent": "from the header",
            "query.user-agent": "from the query",
        })

        self.assertEqual(
            ["user-agent"],
            [name for name in content if name.lower() == "user-agent"])
        self.assertEqual("from the query", content["user-agent"])

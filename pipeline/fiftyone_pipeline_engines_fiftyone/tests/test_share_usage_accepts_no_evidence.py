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

"""The usage sharing element accepts no evidence, so a pipeline's accepted
evidence, and the cache keys, ETag and Vary header built from it, never
depend on it. It shares what it finds in the flow data and in the web
request instead, by the same rules as before."""

import unittest

from flask import Flask, request

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

# No JavaScript or set header elements, so the filters are those of the
# usage sharing element and of UserAgentElement alone.
NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


class UserAgentElement(FlowElement):
    """A stand-in for an engine, accepting the User-Agent alone."""

    def __init__(self):
        super(UserAgentElement, self).__init__()
        self.datakey = "useragent"

    def process_internal(self, flowdata):
        pass

    def get_evidence_key_filter(self):
        return BasicListEvidenceKeyFilter(["header.user-agent"])


def usage_element(**settings):
    """A usage sharing element that keeps what it would share, because its
    package size is never reached, and sends nothing."""

    return ShareUsage(
        requested_package_size=1000, endpoint="http://127.0.0.1:9",
        **settings)


def pipeline_with(usage):
    return PipelineBuilder(NO_DEFAULT_ELEMENTS) \
        .add(UserAgentElement()).add(usage).build()


def request_evidence(headers, path="/"):
    """The evidence the web integration makes from a request."""

    with Flask(__name__).test_request_context(path, headers=headers):
        return webevidence(request)


class ShareUsageAcceptsNoEvidenceTests(unittest.TestCase):

    def test_the_pipeline_accepts_no_header_for_usage_sharing(self):
        usage = usage_element()
        pipeline = pipeline_with(usage)

        for key in ("header.if-none-match", "header.x-test",
                    "cookie.51d_screenpixelswidth", "server.client-ip"):
            self.assertFalse(usage.get_evidence_key_filter()
                             .filter_evidence_key(key), key)
            self.assertFalse(any(
                element.filter_evidence_key(key)
                for element in pipeline.flow_elements), key)
        self.assertTrue(any(
            element.filter_evidence_key("header.user-agent")
            for element in pipeline.flow_elements))

    def test_a_revalidation_has_the_same_accepted_evidence(self):
        """The ETag of a client-side endpoint hashes the evidence the
        pipeline accepts, so a revalidation, which adds If-None-Match, has
        to leave that evidence as it was."""

        pipeline = pipeline_with(usage_element())
        accepted = []
        for headers in ({"User-Agent": CHROME},
                        {"User-Agent": CHROME, "If-None-Match": '"a-tag"'}):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add_from_dict(request_evidence(headers))
            flowdata.process()
            accepted.append(dict(flowdata.evidence.get_all()))

        self.assertEqual(accepted[0], accepted[1])
        self.assertNotIn("header.if-none-match", accepted[1])

    def test_the_web_request_is_shared_by_the_same_rules(self):
        usage = usage_element(header_blacklist=["x-blocked"])
        flowdata = pipeline_with(usage).create_flowdata()
        flowdata.evidence.add_from_dict(request_evidence({
            "User-Agent": CHROME,
            "X-Test": "only usage sharing reads this",
            "X-Blocked": "never shared",
            "Cookie": "51D_ScreenPixelsWidth=1920; other=private",
        }, "/?51D_GetHighEntropyValues=abc&password=secret"))
        flowdata.process()

        shared = "".join(usage.share_data)
        self.assertIn(
            '<header Name="x-test">only usage sharing reads this</header>',
            shared)
        self.assertIn('<header Name="user-agent">', shared)
        self.assertIn(
            '<cookie Name="51D_ScreenPixelsWidth">1920</cookie>', shared)
        self.assertIn(
            '<query Name="51D_GetHighEntropyValues">abc</query>', shared)
        for left_out in ('Name="x-blocked"', 'Name="cookie"', "private",
                         "secret", "http-request"):
            self.assertNotIn(left_out, shared)

    def test_a_key_in_both_places_is_shared_once_with_the_evidence_value(self):
        usage = usage_element()
        flowdata = pipeline_with(usage).create_flowdata()
        flowdata.evidence.add_from_dict(
            request_evidence({"X-Test": "from the request"}))
        flowdata.evidence.add("header.x-test", "from the evidence")
        flowdata.process()

        shared = "".join(usage.share_data)
        self.assertEqual(1, shared.count('Name="x-test"'))
        self.assertIn(
            '<header Name="x-test">from the evidence</header>', shared)

    def test_evidence_added_by_hand_is_shared_as_before(self):
        usage = usage_element()
        flowdata = pipeline_with(usage).create_flowdata()
        flowdata.evidence.add("header.user-agent", CHROME)
        flowdata.evidence.add("header.x-test", "by hand")
        flowdata.evidence.add("cookie.51D_ScreenPixelsWidth", "1920")
        flowdata.evidence.add("cookie.other", "private")
        flowdata.evidence.add("server.client-ip", "203.0.113.42")
        flowdata.process()

        shared = "".join(usage.share_data)
        self.assertIn('<header Name="x-test">by hand</header>', shared)
        self.assertIn(
            '<cookie Name="51D_ScreenPixelsWidth">1920</cookie>', shared)
        self.assertIn("<ClientIP>203.0.113.42</ClientIP>", shared)
        self.assertNotIn("private", shared)

    def test_a_repeat_is_told_apart_by_what_would_be_shared(self):
        """The tracker's hash is of the values that would be shared, so a
        header no other element accepts still tells two requests apart,
        and a repeat of the same request is shared once."""

        usage = usage_element()
        pipeline = pipeline_with(usage)
        for value in ("first", "first", "second"):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add_from_dict(
                request_evidence({"User-Agent": CHROME, "X-Test": value}))
            flowdata.process()

        self.assertEqual(2, len(usage.share_data))


if __name__ == "__main__":
    unittest.main()

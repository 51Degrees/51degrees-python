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
Rules of usage sharing the element meets and no other test holds. The
billing keys are shared whatever the settings, the session cookie is read
from the web request when the Evidence does not hold it, and an entry
shared again takes the time it was shared again.
"""

import gzip
import re
import unittest
from unittest import mock

import requests
from flask import Flask, request

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage
from fiftyone_pipeline_engines_fiftyone.share_usage_tracker import \
    ShareUsageTracker

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The package size is never reached, so the element keeps what it would
# share and sends nothing until it is closed.
QUEUE_ONLY = {
    "requested_package_size": 1000,
    "endpoint": "http://127.0.0.1:9",
}

# The tracker reads the time through this name.
TIME = "fiftyone_pipeline_engines_fiftyone.share_usage_tracker.time.time"

INTERVAL_SECONDS = 60
START = 1000000.0

RESOURCE_KEY = "AQS5HKcyAAAA"
LICENSE_KEY = "LICENCEKEYVALUE"


def sent_on_close(usage):
    """Closes the element, which sends what it has queued, and returns each
    record it posted. The post is answered without leaving the process."""
    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


class BillingKeyTests(unittest.TestCase):

    def test_both_billing_keys_are_shared_whatever_the_settings(self):
        # usage-sharing-element.md line 77, "the filter function MUST
        # return true for both, whatever the configuration".
        for settings in (
                {},
                {"share_all": True},
                {"query_whitelist": [], "header_blacklist": ["x-one"]},
                {"track_session": True, "cookie": "sessionid"}):
            with self.subTest(**{k: str(v) for k, v in settings.items()}):
                usage = ShareUsage(**settings, **QUEUE_ONLY)
                pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
                    .add(usage).build()
                flowdata = pipeline.create_flowdata()
                flowdata.evidence.add("header.user-agent", "agent value")
                flowdata.evidence.add("fiftyone.resource-key", RESOURCE_KEY)
                flowdata.evidence.add("fiftyone.license-key", LICENSE_KEY)
                flowdata.process()
                records = sent_on_close(usage)

                self.assertEqual(1, len(records))
                self.assertRegex(
                    records[0],
                    'Name="resource-key"[^>]*>' + RESOURCE_KEY)
                self.assertRegex(
                    records[0],
                    'Name="license-key"[^>]*>' + LICENSE_KEY)


class SessionCookieFromTheWebRequestTests(unittest.TestCase):

    def test_the_session_cookie_is_read_from_the_web_request(self):
        # usage-sharing-element.md line 83, the element "MUST read the
        # cookie named by the session cookie name option from the same two
        # places as the values it shares". The Evidence here holds the web
        # request but not the cookie, so only the request has it.
        app = Flask(__name__)
        usage = ShareUsage(
            track_session=True, cookie="sessionid", **QUEUE_ONLY)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
        for session in ("first", "first", "second"):
            with app.test_request_context("/", headers={
                    "User-Agent": "agent value",
                    "Cookie": "sessionid=" + session}):
                evidence = webevidence(request)
                self.assertIn("server.http-request", evidence)
                evidence = {key: value for key, value in evidence.items()
                            if not key.lower().startswith("cookie.")}
                flowdata = pipeline.create_flowdata()
                flowdata.evidence.add_from_dict(evidence)
                flowdata.process()
        records = sent_on_close(usage)

        # The repeat in the first session is not shared, and the same
        # Evidence from the second session is, and the cookie is not.
        self.assertEqual(2, len(records))
        for record in records:
            self.assertIn("agent value", record)
            self.assertNotIn('Name="sessionid"', record)


class TimeOfAnEntrySharedAgainTests(unittest.TestCase):

    def share_at(self, tracker, key, seconds):
        """Track the key as the element does, storing the time when it is
        shared, with the clock at the given seconds after the start."""
        with mock.patch(TIME, return_value=START + seconds):
            shared = tracker.track(key)
            if shared:
                tracker.set_cache_value(key)
            return shared

    def test_an_entry_shared_again_takes_the_time_it_was_shared(self):
        # usage-sharing-element.md line 280, "Evidence matching an entry
        # shared the interval or more ago MUST be shared, and the entry's
        # time MUST be set to the time it is shared."
        tracker = ShareUsageTracker(interval=INTERVAL_SECONDS)
        self.assertTrue(self.share_at(tracker, "a", 0))
        self.assertTrue(self.share_at(tracker, "a", INTERVAL_SECONDS))

        # Measured from the second share, not the first.
        self.assertFalse(
            self.share_at(tracker, "a", 2 * INTERVAL_SECONDS - 1))
        self.assertTrue(self.share_at(tracker, "a", 2 * INTERVAL_SECONDS))


if __name__ == "__main__":
    unittest.main()

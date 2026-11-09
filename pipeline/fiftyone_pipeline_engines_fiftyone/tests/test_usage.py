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

import platform
import sys
import threading
from time import sleep
import unittest
from wsgiref.simple_server import make_server
import gzip

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage
from flask import Flask, request, render_template
import requests

testHost = "127.0.0.1"
testPort = 5000
testEndpoint = f"http://{testHost}:{testPort}"

shareUsageVersion = "1.1"


class ReceiverThread(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server(testHost, testPort, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

    def get_received(self):
        return self.server.get_app().received

app = Flask(__name__)
app.received = []

@app.route('/', methods=['POST'])
def server():
    data = gzip.decompress(request.data).decode("utf8")
    str(app.received.append(data))
    return ""


######################################
# The Tests

class UsageTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.startReceiver()

    def setUp(self):
        app.received = []

    @classmethod
    def tearDownClass(cls):
        cls.stopReceiver()

    @classmethod
    def startReceiver(cls):
        cls.receiver = ReceiverThread(app)
        cls.receiver.start()

    @classmethod
    def stopReceiver(cls):
        cls.receiver.shutdown()

    def waitForUsageThreads(self):
        # necessary for context switching and
        # allowing the thread pool in ShareUsage to start sending data and release the GIL
        sleep(0.1)

    def test_data_received(self):
        """!
        Check that data is received from the share usage element. 
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint = testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        
    def test_data_correct(self):
        """!
        Check that the data received from the share usage element is correct.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.process()

        self.waitForUsageThreads()
        self.assertIsNotNone(app.received[0])
        self.assertGreater(len(app.received[0]), 0)
        self.assertRegex(app.received[0], f"^<Devices version=\"{shareUsageVersion}\"><Device>.*")
        self.assertRegex(app.received[0], ".*</Device></Devices>$")
        self.assertIn("<Language>Python</Language>", app.received[0])
        self.assertIn(f"<LanguageVersion>{platform.python_version()}</LanguageVersion>", app.received[0])
        self.assertIn(f"<Platform>{platform.system()} {platform.release()}</Platform>", app.received[0])
        self.assertIn("<FlowElement>ShareUsage</FlowElement>", app.received[0])

    def test_includes_header(self):
        """!
        Check that the data received from the share usage element contains the
        headers which were in the evidence.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        uaValue = "some user agent.."
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", uaValue)
        flowdata.process()

        self.waitForUsageThreads()
        self.assertIsNotNone(app.received[0])
        self.assertGreater(len(app.received[0]), 0)
        self.assertIn(f"<header Name=\"user-agent\">{uaValue}</header>", app.received[0]);

    def test_client_ip(self):
        """!
        Check that the data received from the share usage element includes
        the client IP from the evidence.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        ip = "1.2.3.4"
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("server.client-ip", ip)
        flowdata.process()

        self.waitForUsageThreads()
        self.assertIsNotNone(app.received[0])
        self.assertGreater(len(app.received[0]), 0)
        self.assertIn(f"<ClientIP>{ip}</ClientIP>", app.received[0]);

    def test_two_events_first(self):
        """!
        Check that a single event is not sent when the requested package
        size is 2.
        """

        usage = ShareUsage(
            requested_package_size=2,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 0)

    def test_two_events_second(self):
        """!
        Check that a single event is not sent when the requested package
        size is 2.
        """

        usage = ShareUsage(
            requested_package_size=2,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata1 = pipeline.create_flowdata()
        flowdata1.evidence.add("header.user-agent", "ua 1")
        flowdata1.process()
        flowdata2 = pipeline.create_flowdata()
        flowdata2.evidence.add("header.user-agent", "ua 2")
        flowdata2.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("ua 1", app.received[0])
        self.assertIn("ua 2", app.received[0])

    def test_ignore_headers(self):
        """!
        Check that the share usage element respects the headerBlacklist.
        When header names are added to the list, values for them should
        not be included in the data shared.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            header_blacklist=[ "x-forwarded-for", "forwarded-for" ])

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.evidence.add("header.x-forwarded-for", "5.6.7.8")
        flowdata.evidence.add("header.forwarded-for", "2001::")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertNotIn("x-forwarded-for", app.received[0])
        self.assertNotIn("forwarded-for", app.received[0])

    def test_queue_cleared(self):

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertEqual(len(usage.share_data), 0)

    def test_session_and_sequence(self):
        """!
        Check that session and sequence values are included.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.session-id", "1")
        flowdata.evidence.add("query.sequence", "1")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("<SessionId>1</SessionId>", app.received[0])
        # The Sequence Element is the first element, so it has added one to the
        # sequence by the time usage sharing reads it.
        self.assertIn("<Sequence>2</Sequence>", app.received[0])

    def test_invalid_char(self):
        """!
        Check that invalid characters are escaped correctly.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        replacementChar = chr(int("0xFFFD", 16))

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "1ƌ2")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertNotIn("ƌ", app.received[0])
        self.assertIn(replacementChar, app.received[0])
        self.assertIn(f"<header Name=\"user-agent\" replaced=\"true\">1{replacementChar}2</header>", app.received[0])

    def test_truncated_value(self):
        """!
        Check that long values are truncated correctly.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        ua = "X" * 1000

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", ua)
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("truncated=\"true\"", app.received[0])
        self.assertNotIn(ua, app.received[0])
        self.assertIn(f'<header Name="user-agent" truncated="true">{"X" * 512}</header>', app.received[0])

    def test_send_more_than_once(self):
        """!
        Check that the queue of data is correctly reset, and used for the
        next set of requests.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata1 = pipeline.create_flowdata()
        flowdata1.evidence.add("header.user-agent", "ua 1")
        flowdata1.process()
        flowdata2 = pipeline.create_flowdata()
        flowdata2.evidence.add("header.user-agent", "ua 2")
        flowdata2.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 2)
        self.assertEqual(len(usage.share_data), 0)
        received = "\n".join(app.received)
        self.assertIn("ua 1", received)
        self.assertIn("ua 2", received)

    def test_low_percentage(self):
        """!
        Check that small portion sharing is done correctly.
        """

        usage = ShareUsage(
            requested_package_size=10,
            share_percentage=0.01,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()

        requiredEvents = 0
        while len(app.received) == 0 and requiredEvents <= 10000:
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("server.client-ip", "1.2.3.4")
            flowdata.evidence.add("header.user-agent", f"ua {requiredEvents}")
            flowdata.process()
            requiredEvents = requiredEvents + 1

        self.waitForUsageThreads()

        # On average, the number of required events should be around
        # 1000. However, as it's chance based it can vary
        # significantly. We only want to catch any gross errors so just
        # make sure the value is of the expected order of magnitude.
        self.assertGreater(requiredEvents, 100,
            "Expected the number of required events to be at least " +
            f"100, but was actually '{requiredEvents}'")
        self.assertLess(requiredEvents, 10000,
            "Expected the number of required events to be less than " +
            f"10,000, but was actually '{requiredEvents}'")

    def test_includes_header(self):
        """!
        Check that XML characters are escaped correctly.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", '"\'&><')
        flowdata.process()

        self.waitForUsageThreads()
        self.assertIsNotNone(app.received[0])
        self.assertGreater(len(app.received[0]), 0)
        self.assertIn('&quot;', app.received[0])
        self.assertIn('&apos;', app.received[0])
        self.assertIn('&lt;', app.received[0])
        self.assertIn('&gt;', app.received[0])
        self.assertIn('&amp;', app.received[0])


    def test_default_shares_only_accepted_evidence(self):
        """!
        Check that with no options the element shares headers and the
        51Degrees cookies and parameters, and leaves out other cookies, the
        Cookie header, and other query string and form parameters.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.evidence.add("cookie.51d_screenpixelswidth", "1080")
        flowdata.evidence.add("query.51d_gethighentropyvalues", "hev")
        flowdata.evidence.add("cookie.sessionid", "cookie value")
        flowdata.evidence.add("header.cookie", "sessionid=header value")
        flowdata.evidence.add("query.password", "password value")
        flowdata.evidence.add("query.id.email", "email value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn('<header Name="user-agent">some user agent</header>', app.received[0])
        self.assertIn('<cookie Name="51d_screenpixelswidth">1080</cookie>', app.received[0])
        self.assertIn('<query Name="51d_gethighentropyvalues">hev</query>', app.received[0])
        self.assertNotIn("cookie value", app.received[0])
        self.assertNotIn("header value", app.received[0])
        self.assertNotIn("password value", app.received[0])
        self.assertNotIn("email value", app.received[0])

    def test_never_shared_evidence(self):
        """!
        Check that the email address, the salt for hashed email
        identifiers, the query string and the path are not shared, though
        the rules for their prefixes would share them.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.evidence.add("id.email", "email value")
        flowdata.evidence.add("header.id.salt", "salt value")
        flowdata.evidence.add("server.request-query", "query string value")
        flowdata.evidence.add("server.request-path", "path value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("some user agent", app.received[0])
        self.assertNotIn("email value", app.received[0])
        self.assertNotIn("salt value", app.received[0])
        self.assertNotIn("query string value", app.received[0])
        self.assertNotIn("path value", app.received[0])

    def test_share_all(self):
        """!
        Check that sharing all evidence shares what the other rules leave
        out, but not the evidence that is never shared.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            share_all=True)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("cookie.sessionid", "cookie value")
        flowdata.evidence.add("query.campaign", "campaign value")
        flowdata.evidence.add("query.id.email", "email value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn('<cookie Name="sessionid">cookie value</cookie>', app.received[0])
        self.assertIn('<query Name="campaign">campaign value</query>', app.received[0])
        self.assertNotIn("email value", app.received[0])

    def test_parameter_names_with_dots(self):
        """!
        Check that a query string parameter whose name contains a dot is
        matched by its whole name against the parameters to share.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            query_whitelist=["valid.email"])

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("query.valid.email", "valid value")
        flowdata.evidence.add("query.valid", "first part value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn('<query Name="valid.email">valid value</query>', app.received[0])
        self.assertNotIn("first part value", app.received[0])

    def test_empty_query_whitelist(self):
        """!
        Check that an empty list of parameters to share shares only those
        starting 51D_, and that None shares every parameter.
        """

        for query_whitelist, shared in (([], False), (None, True)):
            app.received = []
            usage = ShareUsage(
                requested_package_size=1,
                endpoint=testEndpoint,
                query_whitelist=query_whitelist,
                header_blacklist=["x-secret"])

            pipeline = (PipelineBuilder())\
                .add(usage)\
                .build()
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("query.51d_param", "fiftyone value")
            flowdata.evidence.add("query.campaign", "campaign value")
            flowdata.process()

            self.waitForUsageThreads()
            self.assertEqual(len(app.received), 1)
            self.assertIn("fiftyone value", app.received[0])
            self.assertEqual("campaign value" in app.received[0], shared)

    def test_session_cookie(self):
        """!
        Check that with session tracking on the session cookie is kept in
        the evidence, but neither it nor any other ordinary cookie is
        shared.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            cookie="sessionid",
            track_session=True)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.evidence.add("cookie.sessionid", "session value")
        flowdata.evidence.add("cookie._ga", "analytics value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertTrue(usage.get_evidence_key_filter().filter_evidence_key("cookie.sessionid"))
        self.assertEqual(len(app.received), 1)
        self.assertIn("some user agent", app.received[0])
        self.assertNotIn("session value", app.received[0])
        self.assertNotIn("analytics value", app.received[0])

    def test_session_cookie_without_session_tracking(self):
        """!
        Check that session tracking is off by default, and that naming the
        session cookie then has no effect. The cookie is not kept, and
        evidence already shared is not shared again for a new session.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            cookie="sessionid")

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        for session in ("session value 1", "session value 2"):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("header.user-agent", "repeated user agent")
            flowdata.evidence.add("cookie.sessionid", session)
            flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertNotIn("session value", app.received[0])
        self.assertFalse(usage.get_evidence_key_filter().filter_evidence_key("cookie.sessionid"))
        self.assertFalse(usage.track_session)

    def test_session_tracking(self):
        """!
        Check that with session tracking on, evidence already shared is
        shared again for a new session but not for a repeat in the same
        session, and that the session cookie is not shared.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            cookie="sessionid",
            track_session=True)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        for session in ("session value 1", "session value 1", "session value 2"):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("header.user-agent", "repeated user agent")
            flowdata.evidence.add("cookie.sessionid", session)
            flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 2)
        received = "\n".join(app.received)
        self.assertEqual(received.count("repeated user agent"), 2)
        self.assertNotIn("session value", received)

    def test_ordinary_cookie_with_header_blacklist(self):
        """!
        Check that an ordinary cookie is left out without an error when
        some headers are not to be shared.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            header_blacklist=["x-secret"])

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "some user agent")
        flowdata.evidence.add("header.x-secret", "secret value")
        flowdata.evidence.add("cookie.csrftoken", "token value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("some user agent", app.received[0])
        self.assertNotIn("secret value", app.received[0])
        self.assertNotIn("token value", app.received[0])

    def test_repeat_with_new_sequence_not_shared(self):
        """!
        Check that a request differing from one already shared only in
        its session id and sequence number is not shared again.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        for session, sequence in (("session 1", "1"), ("session 2", "2")):
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add("header.user-agent", "repeated user agent")
            flowdata.evidence.add("query.session-id", session)
            flowdata.evidence.add("query.sequence", sequence)
            flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("<SessionId>session 1</SessionId>", app.received[0])

    def test_evidence_without_a_prefix(self):
        """!
        Check that evidence whose key has no prefix is shared without an
        error.
        """

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint)

        pipeline = (PipelineBuilder())\
            .add(usage)\
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("nodot", "no prefix value")
        flowdata.process()

        self.waitForUsageThreads()
        self.assertEqual(len(app.received), 1)
        self.assertIn("<nodot>no prefix value</nodot>", app.received[0])

    # zzz is to make this test run last so no other tests depend on the receiver anymore
    # we depend on python unittests ordering tests alphabetically, which is not ideal, but works for now
    def test_zzz_timeout(self):
        # this tests just verifies that there is a timeout and that the tests actually complete
        # even if there is no server listening, so we shut it down right away
        self.__class__.stopReceiver()

        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            request_timeout=1 #really short request time out
        )

        pipeline = (PipelineBuilder()) \
            .add(usage) \
            .build()
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", '"\'&><')
        flowdata.process()

        self.assertTrue(True)

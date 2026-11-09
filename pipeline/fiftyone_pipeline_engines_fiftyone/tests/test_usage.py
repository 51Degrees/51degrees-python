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

import contextlib
import io
import platform
import re
import sys
import threading
import time
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
# When each request arrived, whatever the answer.
app.attempts = []
# The status the receiver answers with. Only data it accepts is received.
app.status = 200
# The content the receiver answers with.
app.body = ""

@app.route('/', methods=['POST'])
def server():
    app.attempts.append(time.monotonic())
    data = gzip.decompress(request.data).decode("utf8")
    if app.status == 200:
        app.received.append(data)
    return app.body, app.status


def client_ips(received):
    """!
    The client IPs in the usage data received.
    """
    ips = []
    for data in received:
        ips.extend(re.findall("<ClientIP>([^<]*)</ClientIP>", data))
    return ips


######################################
# The Tests

class UsageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.startReceiver()

    def setUp(self):
        app.received = []
        app.attempts = []
        app.status = 200
        app.body = ""
        self.requests = 0
        self.logs = []

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

    def wait_for(self, condition, message):
        """!
        Wait for a condition, failing the test with the message if it is not
        met within 30 seconds.
        """
        end = time.monotonic() + 30
        while not condition():
            if time.monotonic() > end:
                self.fail(message())
            sleep(0.02)

    def back_off_pipeline(self, **settings):
        """!
        A pipeline whose usage sharing element sends each entry on its own.
        The element is closed when the test ends.
        """
        usage = ShareUsage(
            requested_package_size=1,
            endpoint=testEndpoint,
            **settings)
        pipeline = PipelineBuilder().add(usage).build()
        self.addCleanup(usage.close)
        return usage, pipeline

    def process_unique(self, pipeline):
        """!
        Process a request whose evidence no other request has, and return
        its client IP.
        """
        ip = f"10.0.{self.requests // 250}.{self.requests % 250 + 1}"
        self.requests += 1
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("server.client-ip", ip)
        flowdata.process()
        return ip

    def fail_sends(self, pipeline, count):
        """!
        Process requests one at a time, waiting for each to be sent, so each
        is a separate failed send.
        """
        app.status = 500
        for sent in range(1, count + 1):
            self.process_unique(pipeline)
            self.wait_for(
                lambda: len(app.attempts) == sent,
                lambda: f"Send {sent} was not made.")

    def test_back_off_pauses_then_drains_queue(self):
        """!
        Ten failed sends pause sending for two seconds, the defaults.
        Nothing is sent during the pause, the evidence processed during it
        is queued, and all of it is sent once the pause ends and the
        service answers, with no more requests processed.
        """

        usage, pipeline = self.back_off_pipeline()
        self.fail_sends(pipeline, 10)
        paused_at = time.monotonic()

        queued = [self.process_unique(pipeline) for i in range(5)]
        sleep(0.7)
        self.assertEqual(
            len(app.attempts), 10,
            "Sends were made during the pause that ten failed sends "
            "should have started.")

        app.status = 200
        self.wait_for(
            lambda: all(ip in client_ips(app.received) for ip in queued),
            lambda: "The evidence processed during the pause was not all "
                f"sent once the service answered. Sent: "
                f"{client_ips(app.received)}")
        waited = app.attempts[10] - paused_at
        self.assertGreaterEqual(
            waited, 1.5,
            f"Sending resumed {waited:.2f} seconds after the pause started, "
            "before the two second pause ended.")

    def test_back_off_close_while_paused(self):
        """!
        Closing while paused returns at once rather than waiting for the
        pause to end, and sends nothing.
        """

        usage, pipeline = self.back_off_pipeline()
        self.fail_sends(pipeline, 10)
        self.process_unique(pipeline)
        self.process_unique(pipeline)

        start = time.monotonic()
        usage.close()
        took = time.monotonic() - start

        self.assertLess(
            took, 1.5,
            f"Closing took {took:.2f} seconds, as it waited for the pause.")
        self.assertEqual(
            len(app.attempts), 10,
            "A send was made during the pause or when closing.")

    def test_back_off_delay_grows_to_maximum(self):
        """!
        Each failed send after a pause multiplies the delay, and the delay
        stops growing at the maximum.
        """

        usage, pipeline = self.back_off_pipeline(
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=0.5,
            max_recovery_delay_seconds=1.0)
        app.status = 500
        for i in range(40):
            self.process_unique(pipeline)

        self.wait_for(
            lambda: len(app.attempts) >= 4,
            lambda: "Fewer than four sends were made.")
        gaps = [app.attempts[i] - app.attempts[i - 1] for i in range(1, 4)]
        shown = ", ".join(f"{gap:.2f}" for gap in gaps)
        self.assertGreaterEqual(
            gaps[0], 0.4,
            f"The first pause was not the initial delay. Gaps: {shown}")
        self.assertGreaterEqual(
            gaps[1], 0.9,
            f"The second pause was not doubled. Gaps: {shown}")
        self.assertTrue(
            0.9 <= gaps[2] < 1.9,
            f"The third pause was not held at the maximum. Gaps: {shown}")

    def test_back_off_full_queue_drops_new_evidence(self):
        """!
        When the queue fills during a pause, new evidence is dropped and
        what was queued first is sent once sending resumes.
        """

        usage, pipeline = self.back_off_pipeline(
            max_queue_size=4,
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=2,
            max_recovery_delay_seconds=2)
        self.fail_sends(pipeline, 1)

        kept = [self.process_unique(pipeline) for i in range(4)]
        dropped = [self.process_unique(pipeline) for i in range(6)]
        app.status = 200

        self.wait_for(
            lambda: all(ip in client_ips(app.received) for ip in kept),
            lambda: "The evidence queued during the pause was not all sent. "
                f"Sent: {client_ips(app.received)}")
        sleep(0.5)
        for ip in dropped:
            self.assertNotIn(
                ip, client_ips(app.received),
                "Evidence processed when the queue was full was sent.")

    def test_full_queue_logs_without_a_message_per_entry(self):
        """!
        Entries discarded because the queue is full are logged, but not with
        a message for each entry discarded.
        """

        usage, pipeline = self.back_off_pipeline(
            max_queue_size=4,
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=2,
            max_recovery_delay_seconds=2)
        usage._log = lambda level, message: self.logs.append((level, message))
        self.fail_sends(pipeline, 1)
        self.logs.clear()

        for i in range(10):
            self.process_unique(pipeline)

        full = [log for log in self.logs if "full" in log[1]]
        self.assertGreaterEqual(
            len(full), 1, "Discarding entries was not logged.")
        self.assertLess(
            len(full), 6, "A message was logged for each entry discarded.")
        self.assertEqual("warning", full[0][0])

    def test_failed_answer_logs_status_and_content(self):
        """!
        A send answered with anything other than 200 logs the status code and
        the content of the answer.
        """

        usage, pipeline = self.back_off_pipeline()
        usage._log = lambda level, message: self.logs.append((level, message))
        app.body = "the service says no"

        self.fail_sends(pipeline, 1)

        self.wait_for(
            lambda: any("500" in log[1] for log in self.logs),
            lambda: f"The status code was not logged. Logged: {self.logs}")
        failed = [log for log in self.logs if "500" in log[1]][0]
        self.assertIn("the service says no", failed[1])

    def test_failed_send_prints_nothing(self):
        """!
        A send that cannot be made is logged and does not print.
        """

        usage, pipeline = self.back_off_pipeline(request_timeout=1)
        usage._log = lambda level, message: self.logs.append((level, message))
        usage.endpoint = "http://127.0.0.1:1"
        printed = io.StringIO()

        with contextlib.redirect_stdout(printed):
            self.process_unique(pipeline)
            self.wait_for(
                lambda: any("failed sending" in log[1] for log in self.logs),
                lambda: f"The failed send was not logged. Logged: {self.logs}")

        self.assertEqual("", printed.getvalue())

    def test_message_holds_up_to_twice_the_package_size(self):
        """!
        A message holds the requested package size or more entries, up to
        twice the package size, so a queue that filled during a pause drains
        in fewer messages.
        """

        usage = ShareUsage(
            requested_package_size=2,
            endpoint=testEndpoint,
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=1,
            max_recovery_delay_seconds=1)
        pipeline = PipelineBuilder().add(usage).build()
        self.addCleanup(usage.close)
        app.status = 500
        self.process_unique(pipeline)
        self.process_unique(pipeline)
        self.wait_for(
            lambda: len(app.attempts) == 1,
            lambda: "The first send was not made.")
        for i in range(6):
            self.process_unique(pipeline)

        app.status = 200
        self.wait_for(
            lambda: len(client_ips(app.received)) == 6,
            lambda: f"Not all entries were sent: {client_ips(app.received)}")

        sizes = [len(client_ips([data])) for data in app.received]
        self.assertEqual(
            [4, 2], sizes,
            "The messages did not hold up to twice the package size.")

    def test_close_sends_fewer_entries_than_the_package_size(self):
        """!
        Closing sends the entries still queued, even when there are fewer
        than the requested package size.
        """

        usage = ShareUsage(
            requested_package_size=5,
            endpoint=testEndpoint)
        pipeline = PipelineBuilder().add(usage).build()
        ips = [self.process_unique(pipeline) for i in range(2)]
        self.assertEqual([], app.received)

        usage.close()

        self.assertEqual(ips, client_ips(app.received))

    def test_back_off_invalid_settings(self):
        """!
        Settings the pause cannot work with are rejected.
        """

        for settings in [
                {"failures_to_enter_recovery": 0},
                {"failures_to_enter_recovery": 101},
                {"failures_window_seconds": 0},
                {"initial_recovery_delay_seconds": 0},
                {"max_recovery_delay_seconds": -1},
                {"recovery_multiplier": 0.5},
                {"max_queue_size": 0}]:
            with self.assertRaises(ValueError, msg=str(settings)):
                ShareUsage(
                    requested_package_size=1,
                    endpoint=testEndpoint,
                    **settings)

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
        self.assertIn("<Sequence>1</Sequence>", app.received[0])

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

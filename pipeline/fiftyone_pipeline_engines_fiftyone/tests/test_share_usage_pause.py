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
Processing while usage sharing is paused after failed sends, as the back-off
section of the usage sharing element specification says. Sending is stood in
for, so no message leaves the process.
"""

import threading
import time
import unittest

from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The longest the tests wait for anything. It only stops a test that would
# otherwise never end, and is never a measure of speed.
GUARD_SECONDS = 30

# How often a test looks again at something it is waiting for.
POLL_SECONDS = 0.01

# A pause far longer than any test, so that it lasts while the test runs.
LONG_PAUSE_SECONDS = 3600

# The number of requests processed while sending is paused.
REQUESTS_DURING_PAUSE = 10


class After(FlowElement):
    """!
    An element after usage sharing, which records that processing reached
    it.
    """

    def __init__(self):
        super(After, self).__init__()
        self.datakey = "after"
        self.properties = {"reached": {"type": "bool"}}

    def process_internal(self, flow_data):
        flow_data.set_element_data(
            ElementDataDictionary(self, {"reached": True}))


class BlockedSend:
    """!
    Stands in for sending a message. The first send fails, which starts a
    pause. Any later send waits on an event that is set only when the test
    ends, so a caller that waited for a send would not return.
    """

    def __init__(self):
        self.release = threading.Event()
        self._lock = threading.Lock()
        # The thread that made each send, in order.
        self.callers = []

    def __call__(self, endpoint, data):
        with self._lock:
            self.callers.append(threading.current_thread())
            first = len(self.callers) == 1
        if not first:
            self.release.wait(GUARD_SECONDS)
        return False


class ShareUsagePauseTests(unittest.TestCase):

    def wait_until(self, condition, message):
        end = time.monotonic() + GUARD_SECONDS
        while not condition():
            if time.monotonic() > end:
                self.fail(message)
            time.sleep(POLL_SECONDS)

    def process(self, pipeline, user_agent):
        """!
        Process a request, returning whether processing reached the element
        after usage sharing.
        """
        flow_data = pipeline.create_flowdata()
        flow_data.evidence.add("header.user-agent", user_agent)
        flow_data.process()
        return flow_data.get("after").get("reached")

    def test_processing_does_not_wait_for_the_pause(self):
        """!
        Requests processed while sending is paused return, reach the
        elements after usage sharing and are queued, and none of them waits
        for a send.
        """

        send = BlockedSend()
        usage = ShareUsage(
            requested_package_size=1,
            endpoint="http://127.0.0.1:9",
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=LONG_PAUSE_SECONDS,
            max_recovery_delay_seconds=LONG_PAUSE_SECONDS)
        usage.send_thread = send
        self.addCleanup(usage.close)
        # Runs before closing, so closing never waits on a held send.
        self.addCleanup(send.release.set)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add(usage).add(After()).build()

        # One failed send starts the pause.
        self.process(pipeline, "before the pause")
        self.wait_until(
            lambda: usage.backoff.remaining(time.monotonic()) > 0,
            "The failed send did not pause sending.")

        reached = []

        def process_during_pause():
            for i in range(REQUESTS_DURING_PAUSE):
                reached.append(self.process(pipeline, f"during pause {i}"))

        worker = threading.Thread(target=process_during_pause, daemon=True)
        worker.start()
        worker.join(GUARD_SECONDS)

        self.assertFalse(
            worker.is_alive(),
            "Processing waited for the pause after failed sends.")
        self.assertEqual(
            [True] * REQUESTS_DURING_PAUSE, reached,
            "Processing during the pause did not reach the element after "
            "usage sharing.")
        self.assertEqual(
            REQUESTS_DURING_PAUSE, len(usage.share_data),
            "The requests processed during the pause were not queued.")
        self.assertEqual(
            1, len(send.callers),
            "A message was sent during the pause.")
        self.assertNotIn(
            worker, send.callers,
            "The processing thread made a send.")


if __name__ == "__main__":
    unittest.main()

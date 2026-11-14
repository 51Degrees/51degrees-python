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
Processing while usage sharing is paused after failed sends, and the
messages logged when a pause starts, is lengthened and ends, as the back-off
section of the usage sharing element specification says. Sending is stood in
for, so no message leaves the process.
"""

import re
import threading
import time
import unittest

from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.logger import Logger
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

# The first pause, and what a failed send when it ends multiplies it by.
# Both are exact in binary, so the delays are logged exactly.
FIRST_PAUSE_SECONDS = 0.25
RECOVERY_MULTIPLIER = 3
LONGER_PAUSE_SECONDS = FIRST_PAUSE_SECONDS * RECOVERY_MULTIPLIER


def numbers_in(message):
    """!
    The numbers written in a message.
    """
    return [float(number)
            for number in re.findall(r"\d+(?:\.\d+)?", message)]


class Recorder(Logger):
    """!
    A pipeline logger that keeps the level and text of each message, and
    lets a test wait for the messages it expects.
    """

    def __init__(self):
        super(Recorder, self).__init__("info")
        self.logged = []
        self._changed = threading.Condition()

    def log_internal(self, level, log):
        with self._changed:
            self.logged.append((level, log["message"]))
            self._changed.notify_all()

    def wait_for(self, condition):
        """!
        Wait until the messages logged meet the condition, returning False
        if they do not within the guard.
        """
        with self._changed:
            return self._changed.wait_for(
                lambda: condition(list(self.logged)), GUARD_SECONDS)


class ChosenSend:
    """!
    Stands in for sending a message, failing until the test lets sends
    succeed.
    """

    def __init__(self):
        self.succeed = threading.Event()

    def __call__(self, endpoint, data):
        return self.succeed.is_set()


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

    def test_pause_longer_pause_and_resume_are_logged(self):
        """!
        A pause logs a warning giving its delay, a failed send when it ends
        logs a warning giving the longer delay, and the send that succeeds
        after that logs that sending resumed, as information.
        """

        recorder = Recorder()
        send = ChosenSend()
        usage = ShareUsage(
            requested_package_size=1,
            endpoint="http://127.0.0.1:9",
            failures_to_enter_recovery=1,
            initial_recovery_delay_seconds=FIRST_PAUSE_SECONDS,
            max_recovery_delay_seconds=LONG_PAUSE_SECONDS,
            recovery_multiplier=RECOVERY_MULTIPLIER)
        usage.send_thread = send
        self.addCleanup(usage.close)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS) \
            .add_logger(recorder).add(usage).add(After()).build()

        def index_of(logged, matches):
            return next((index for index, (level, message)
                         in enumerate(logged) if matches(level, message)),
                        None)

        def pause_of(seconds):
            return lambda level, message: \
                level == "warning" and seconds in numbers_in(message)

        def resumed(level, message):
            return level == "info" and "resum" in message.lower()

        def logged_once(matches):
            return lambda logged: index_of(logged, matches) is not None

        # The first failed send pauses sending.
        self.process(pipeline, "first")
        self.assertTrue(
            recorder.wait_for(logged_once(pause_of(FIRST_PAUSE_SECONDS))),
            f"No warning gave the {FIRST_PAUSE_SECONDS} second pause. "
            f"Logged: {recorder.logged}")

        # The send made when the pause ends fails, lengthening the pause.
        self.process(pipeline, "second")
        self.assertTrue(
            recorder.wait_for(logged_once(pause_of(LONGER_PAUSE_SECONDS))),
            f"No warning gave the {LONGER_PAUSE_SECONDS} second pause. "
            f"Logged: {recorder.logged}")

        # The send made when the longer pause ends succeeds.
        send.succeed.set()
        self.process(pipeline, "third")
        self.assertTrue(
            recorder.wait_for(logged_once(resumed)),
            "No information message said that sending resumed. "
            f"Logged: {recorder.logged}")

        logged = list(recorder.logged)
        self.assertLess(
            index_of(logged, pause_of(FIRST_PAUSE_SECONDS)),
            index_of(logged, pause_of(LONGER_PAUSE_SECONDS)),
            f"The messages were logged out of order: {logged}")
        self.assertLess(
            index_of(logged, pause_of(LONGER_PAUSE_SECONDS)),
            index_of(logged, resumed),
            f"The messages were logged out of order: {logged}")


if __name__ == "__main__":
    unittest.main()

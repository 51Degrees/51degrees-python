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
Releasing a usage sharing element that was never closed. The garbage
collector releases it on whichever thread it runs, so releasing never waits
for the thread that sends. Sending is stood in for, so no message leaves the
process.
"""

import threading
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The longest the tests wait for anything. It only stops a test that would
# otherwise never end, and is never a measure of speed.
GUARD_SECONDS = 30


class HeldSend:
    """!
    Stands in for sending a message. Each send waits until the test lets it
    go, for longer than the test waits for releasing, so a release that
    waited for the send would still be running when the test looks.
    """

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def __call__(self, endpoint, data):
        self.started.set()
        self.release.wait(GUARD_SECONDS * 2)
        self.finished.set()
        return True


class ShareUsageReleaseTests(unittest.TestCase):

    def test_release_does_not_wait_for_a_send(self):
        """!
        Releasing an element that was not closed returns while a message is
        still being sent, and the message is sent once the send is let go.
        """

        send = HeldSend()
        usage = ShareUsage(
            requested_package_size=1,
            endpoint="http://127.0.0.1:9")
        usage.send_thread = send
        # Lets the held send go however the test ends.
        self.addCleanup(send.release.set)
        pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()

        flow_data = pipeline.create_flowdata()
        flow_data.evidence.add("header.user-agent", "released element")
        flow_data.process()
        self.assertTrue(
            send.started.wait(GUARD_SECONDS),
            "The message was not sent.")

        # The collector calls this when nothing refers to the element. It is
        # called here so the test knows when, and on a thread of its own so
        # that a release that waited does not stop the test.
        releasing = threading.Thread(target=usage.__del__, daemon=True)
        releasing.start()
        releasing.join(GUARD_SECONDS)

        self.assertFalse(
            releasing.is_alive(),
            "Releasing the element waited for the message being sent.")
        self.assertFalse(
            send.finished.is_set(),
            "The send ended before releasing returned, so the test did not "
            "show that releasing does not wait for it.")

        send.release.set()
        self.assertTrue(
            send.finished.wait(GUARD_SECONDS),
            "The message being sent when the element was released did not "
            "finish.")


if __name__ == "__main__":
    unittest.main()

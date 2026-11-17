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
The values that do not change while a usage sharing element lives, written
to its first record and again once an hour, and the process identifier
written to every record.

The rules are those of the specifications repository at commit 07e1fced,
pipeline-specification/pipeline-elements/usage-sharing-element.md. The
tests control the element's clock rather than waiting an hour.
"""

import gzip
import os
import re
import subprocess
import sys
import threading
import unittest
from unittest import mock

import requests

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone import share_usage
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

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

# usage-sharing-element.md lines 138 to 145 at 07e1fced list the invariant
# values, and lines 208 to 210 say "A record that leaves them out has no
# Version, Product, FlowElement, Package, Language, LanguageVersion,
# ServerIP or Platform element".
INVARIANT_ELEMENTS = (
    "Version", "Product", "FlowElement", "Package", "Language",
    "LanguageVersion", "ServerIP", "Platform",
)

HOUR = 3600

# An address from the range RFC 5737 sets aside for documentation.
SERVER_IP = "192.0.2.10"

# How long a test waits for the lookup of the server's address it holds up.
LOOKUP_WAIT_SECONDS = 10

# Lines 124 and 125: "32 hexadecimal digits in groups of 8, 4, 4, 4 and 12
# separated by hyphens", for a version 4 UUID (line 119).
UUID4 = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}"
    r"-[0-9a-fA-F]{12}\Z")


class Clock:
    """A clock the test moves by hand, in seconds."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def sent_on_close(usage):
    """Closes the element, which sends what it has queued, and returns each
    record it posted, in the order written. The post is answered without
    leaving the process."""
    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


def process(pipeline, user_agent):
    """Processes one request. Each test gives each request its own
    User-Agent, so that no request repeats one already shared."""
    with pipeline.create_flowdata() as flowdata:
        flowdata.evidence.add("header.user-agent", user_agent)
        flowdata.process()


def invariants_in(record):
    """The names of the invariant elements a record carries."""
    return [name for name in INVARIANT_ELEMENTS
            if re.search("<" + name + r"[ >]", record)]


def process_ids_in(record):
    return re.findall(r"<ProcessId>([^<]*)</ProcessId>", record)


def element_with_clock(wait_for_server_ip=True):
    """A usage sharing element in a Pipeline of its own, with a clock the
    test moves. Unless asked not to, it waits until the lookup of the
    server's address has ended, as a record written before then does not
    count as carrying the invariant values."""
    usage = ShareUsage(**QUEUE_ONLY)
    if wait_for_server_ip:
        usage._server_ip_found.wait(LOOKUP_WAIT_SECONDS)
    clock = Clock()
    usage.clock = clock
    pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
    return usage, clock, pipeline


class InvariantValuesTests(unittest.TestCase):

    def test_the_first_record_carries_the_invariant_values(self):
        # Line 150: "The invariant values MUST be written to the first
        # record the element writes."
        usage, clock, pipeline = element_with_clock()
        process(pipeline, "first")

        records = sent_on_close(usage)

        self.assertEqual(1, len(records))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[0]))

    def test_records_within_the_hour_leave_the_invariant_values_out(self):
        # Lines 151 to 153: "They MUST be written again to the first record
        # the element writes once an hour or more has passed since it last
        # wrote them. They MUST NOT be written to any other record."
        usage, clock, pipeline = element_with_clock()
        process(pipeline, "first")
        clock.now += 1
        process(pipeline, "second")
        clock.now += HOUR - 1.5
        process(pipeline, "third")

        records = sent_on_close(usage)

        self.assertEqual(3, len(records))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[0]))
        self.assertEqual([], invariants_in(records[1]))
        self.assertEqual([], invariants_in(records[2]))

    def test_the_invariant_values_are_written_again_once_the_hour_is_up(self):
        # Lines 151 and 152, "once an hour or more has passed since it last
        # wrote them", so the hour runs from the record that last carried
        # them, here the one written exactly an hour after the first.
        usage, clock, pipeline = element_with_clock()
        process(pipeline, "first")
        clock.now += HOUR
        process(pipeline, "an hour later")
        clock.now += 1
        process(pipeline, "a second after that")
        clock.now += HOUR - 1
        process(pipeline, "an hour after the second write")
        clock.now += 2 * HOUR + 5
        process(pipeline, "long after")

        records = sent_on_close(usage)

        self.assertEqual(
            [True, True, False, True, True],
            [invariants_in(record) == list(INVARIANT_ELEMENTS)
             for record in records])
        self.assertEqual([], invariants_in(records[2]))

    def test_a_record_that_leaves_them_out_is_otherwise_the_same(self):
        # Lines 208 to 210: a record that leaves the invariant values out
        # "is otherwise the same".
        usage, clock, pipeline = element_with_clock()
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", "first")
            flowdata.evidence.add("query.51D_value", "one")
            flowdata.process()
        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", "second")
            flowdata.evidence.add("query.51D_value", "two")
            flowdata.process()

        later = sent_on_close(usage)[1]

        for name in ("ProcessId", "SessionId", "Sequence", "ClientIP",
                     "DateSent"):
            self.assertIn("<" + name + ">", later)
        self.assertIn('<header Name="user-agent">second</header>', later)
        self.assertIn('<query Name="51D_value">two</query>', later)

    def test_a_record_written_before_the_server_ip_is_known_is_not_counted(
            self):
        # Processing does not wait for the lookup of the server's address,
        # so a record written before it ends has an empty ServerIP. That
        # record does not hold every invariant value, so the next record
        # written once the lookup has ended carries them all, and the hour
        # runs from that record.
        release = threading.Event()
        self.addCleanup(release.set)

        def slow():
            release.wait(LOOKUP_WAIT_SECONDS)
            return SERVER_IP

        with mock.patch.object(share_usage, "host_address", slow):
            usage, clock, pipeline = element_with_clock(
                wait_for_server_ip=False)
            process(pipeline, "before the lookup ends")
            release.set()
            self.assertTrue(usage._server_ip_found.wait(LOOKUP_WAIT_SECONDS))
        clock.now += 1
        process(pipeline, "after the lookup ends")
        clock.now += HOUR - 2
        process(pipeline, "within the hour of that")

        records = sent_on_close(usage)

        self.assertEqual(3, len(records))
        self.assertIn("<ServerIP></ServerIP>", records[0])
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[1]))
        self.assertIn("<ServerIP>" + SERVER_IP + "</ServerIP>", records[1])
        self.assertEqual([], invariants_in(records[2]))

    def test_the_values_go_again_only_in_the_first_record_once_known(self):
        # usage-sharing-element.md lines 152 to 155 at 44d815f8: "When one
        # of them is not yet known as the first record is written, for
        # example a server address still being looked up, the element MUST
        # write all of them again to the first record it writes once that
        # value is known. They MUST NOT be written to any other record."
        # So a second record written while the lookup is still running
        # leaves them out, and the hour runs from the record that carried
        # the address.
        release = threading.Event()
        self.addCleanup(release.set)

        def slow():
            release.wait(LOOKUP_WAIT_SECONDS)
            return SERVER_IP

        with mock.patch.object(share_usage, "host_address", slow):
            usage, clock, pipeline = element_with_clock(
                wait_for_server_ip=False)
            process(pipeline, "first, while the lookup runs")
            clock.now += 1
            process(pipeline, "second, while the lookup runs")
            release.set()
            self.assertTrue(usage._server_ip_found.wait(LOOKUP_WAIT_SECONDS))
        clock.now += 1
        process(pipeline, "first once the address is known")
        clock.now += 1
        process(pipeline, "next after that")
        # An hour less a second after the record that carried the address,
        # and more than an hour after the first record.
        clock.now += HOUR - 2
        process(pipeline, "within the hour of the address")
        clock.now += 1
        process(pipeline, "an hour after the address")

        records = sent_on_close(usage)

        self.assertEqual(6, len(records))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[0]))
        self.assertIn("<ServerIP></ServerIP>", records[0])
        self.assertEqual([], invariants_in(records[1]))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[2]))
        self.assertIn("<ServerIP>" + SERVER_IP + "</ServerIP>", records[2])
        self.assertEqual([], invariants_in(records[3]))
        self.assertEqual([], invariants_in(records[4]))
        self.assertEqual(list(INVARIANT_ELEMENTS), invariants_in(records[5]))
        self.assertIn("<ServerIP>" + SERVER_IP + "</ServerIP>", records[5])


# Writes one record from a new element and prints its ProcessId, so that a
# test can compare the identifiers of two processes.
ONE_RECORD = """
import gzip, re
from unittest import mock
import requests
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage
sent = []
def post(url, headers=None, data=None, **kwargs):
    sent.append(gzip.decompress(data).decode("utf8"))
    return mock.Mock(status_code=200, text="")
usage = ShareUsage(requested_package_size=1000, endpoint="http://127.0.0.1:9")
pipeline = PipelineBuilder({"add_javascript_builder": False,
    "use_setheader_properties": False}).add(usage).build()
flowdata = pipeline.create_flowdata()
flowdata.evidence.add("header.user-agent", "agent")
flowdata.process()
with mock.patch.object(requests, "post", post):
    usage.close()
print(",".join(re.findall("<ProcessId>([^<]*)</ProcessId>", "".join(sent))))
"""


class ProcessIdentifierTests(unittest.TestCase):

    def test_every_record_carries_the_same_identifier(self):
        # Lines 115 and 116: "The element MUST create a process identifier
        # when it is built, and MUST write it to every record as the
        # ProcessId element."
        usage, clock, pipeline = element_with_clock()
        for index in range(5):
            process(pipeline, f"agent {index}")
            clock.now += HOUR / 2

        records = sent_on_close(usage)

        self.assertEqual(5, len(records))
        identifiers = [process_ids_in(record) for record in records]
        for found in identifiers:
            self.assertEqual(1, len(found))
        self.assertEqual(1, len(set(found[0] for found in identifiers)))
        self.assertRegex(identifiers[0][0], UUID4)

    def test_the_identifier_is_written_first_in_the_record(self):
        # The snippet at lines 213 and 214 opens each Device with its
        # ProcessId.
        usage, clock, pipeline = element_with_clock()
        process(pipeline, "first")

        record = sent_on_close(usage)[0]

        self.assertTrue(record.startswith("<Device><ProcessId>"), record)

    def test_a_fresh_element_has_a_new_identifier(self):
        # Lines 128 to 131: a process that starts again creates a new
        # identifier, and "A process that builds more than one Usage
        # Sharing Element ... creates an identifier for each".
        identifiers = []
        for _ in range(2):
            usage, clock, pipeline = element_with_clock()
            process(pipeline, "agent")
            identifiers.extend(process_ids_in(sent_on_close(usage)[0]))

        self.assertEqual(2, len(identifiers))
        self.assertNotEqual(identifiers[0].lower(), identifiers[1].lower())

    def test_a_new_process_has_a_new_identifier(self):
        # Line 128: "The identifier is never stored, so a process that
        # starts again creates a new one."
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            path for path in sys.path if path)
        identifiers = []
        for _ in range(2):
            output = subprocess.run(
                [sys.executable, "-c", ONE_RECORD], env=environment,
                capture_output=True, text=True, timeout=120, check=True)
            identifiers.append(output.stdout.strip())

        for identifier in identifiers:
            self.assertRegex(identifier, UUID4)
        self.assertNotEqual(identifiers[0].lower(), identifiers[1].lower())


if __name__ == "__main__":
    unittest.main()

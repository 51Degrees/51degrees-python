
"""
The elements the web integration adds (Sequence, JSON Builder, JavaScript
Builder and Set Headers) each have a switch that defaults to on, and the
Sequence Element comes first, as the web integration specification says.
"""

import unittest

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class UserElement(FlowElement):

    def __init__(self):
        super(UserElement, self).__init__()
        self.datakey = "user"

    def process_internal(self, flowdata):
        pass


def datakeys(settings=None):
    builder = PipelineBuilder(settings or {})
    builder.add(UserElement())
    pipeline = builder.build()
    return [element.datakey for element in pipeline.flow_elements]


class WebIntegrationElementSwitchTests(unittest.TestCase):

    def testAllElementsAreAddedByDefaultWithSequenceFirst(self):
        self.assertEqual(
            ["sequence", "user", "jsonbundler", "javascriptbuilder",
             "set-headers"],
            datakeys())

    def testSequenceSwitch(self):
        self.assertEqual(
            ["user", "jsonbundler", "javascriptbuilder", "set-headers"],
            datakeys({"add_sequence_element": False}))

    def testJsonBuilderSwitch(self):
        self.assertEqual(
            ["sequence", "user", "javascriptbuilder", "set-headers"],
            datakeys({"add_json_builder_element": False}))

    def testJavaScriptBuilderSwitch(self):
        self.assertEqual(
            ["sequence", "user", "jsonbundler", "set-headers"],
            datakeys({"add_javascript_builder_element": False}))

    def testSetHeadersSwitch(self):
        self.assertEqual(
            ["sequence", "user", "jsonbundler", "javascriptbuilder"],
            datakeys({"add_set_header_element": False}))

    def testExistingJavaScriptSwitchStillDropsThreeElements(self):
        self.assertEqual(
            ["user", "set-headers"],
            datakeys({"add_javascript_builder": False}))

    def testExistingSetHeaderSwitchStillDropsSetHeaders(self):
        self.assertEqual(
            ["sequence", "user", "jsonbundler", "javascriptbuilder"],
            datakeys({"use_setheader_properties": False}))

    def testEverySwitchOff(self):
        self.assertEqual(
            ["user"],
            datakeys({
                "add_sequence_element": False,
                "add_json_builder_element": False,
                "add_javascript_builder_element": False,
                "add_set_header_element": False}))


# The Sequence Element writes Element Data as well as Evidence.
class SequenceElementDataTests(unittest.TestCase):

    def process(self, evidence):
        pipeline = PipelineBuilder({}).build()
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
        return flowdata

    def testFirstRequestHasNewSessionAndSequenceOne(self):
        flowdata = self.process({})
        session_id = flowdata.get("sequence").get("session-id")
        self.assertTrue(session_id)
        self.assertEqual(1, flowdata.get("sequence").get("sequence"))
        self.assertEqual(session_id, flowdata.evidence.get("query.session-id"))
        self.assertEqual(1, flowdata.evidence.get("query.sequence"))

    def testCallbackKeepsSessionAndAddsOne(self):
        flowdata = self.process(
            {"query.session-id": "abc-123", "query.sequence": "3"})
        self.assertEqual("abc-123", flowdata.get("sequence").get("session-id"))
        self.assertEqual(4, flowdata.get("sequence").get("sequence"))
        self.assertEqual("abc-123", flowdata.evidence.get("query.session-id"))
        self.assertEqual(4, flowdata.evidence.get("query.sequence"))

    # The JSON Builder specification requires a top-level entry for each
    # Element Data, excluding only Set Headers, the Cloud Request Engine and
    # Usage Sharing.
    def testSequenceHasAnEntryInTheJsonSentToBrowsers(self):
        flowdata = self.process({})
        entry = flowdata.jsonbundler.json["sequence"]
        self.assertEqual(
            flowdata.get("sequence").get("session-id"), entry["session-id"])
        self.assertEqual(1, entry["sequence"])

    # The JSON is written into the script, so a session id from the query
    # string must not end the script.
    def testSessionIdIsKeptButCannotEndTheScript(self):
        flowdata = self.process({"query.session-id": "</script>"})
        self.assertEqual("</script>", flowdata.get("sequence").get("session-id"))
        self.assertEqual(
            "</script>", flowdata.jsonbundler.json["sequence"]["session-id"])
        self.assertNotIn("</script>", flowdata.javascriptbuilder.javascript)
        self.assertIn(
            "\\u003c/script\\u003e", flowdata.javascriptbuilder.javascript)

    def testSequencePropertiesAreDescribed(self):
        element = PipelineBuilder({}).build().flow_elements[0]
        self.assertEqual("sequence", element.datakey)
        self.assertEqual(
            {"session-id": {"type": "string"}, "sequence": {"type": "int"}},
            element.get_properties())


# The session id and the sequence are read independently, as the Process
# section of the Sequence Element specification says, and the Evidence and the
# Element Data are written from the same values.
class SequenceElementProcessTests(unittest.TestCase):

    def process(self, evidence):
        pipeline = PipelineBuilder({}).build()
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
        data = flowdata.get("sequence")
        session_id = data.get("session-id")
        sequence = data.get("sequence")
        self.assertEqual(session_id, flowdata.evidence.get("query.session-id"))
        self.assertEqual(sequence, flowdata.evidence.get("query.sequence"))
        return session_id, sequence

    def testSequenceWithNoSessionIdCountsUpWithANewId(self):
        session_id, sequence = self.process({"query.sequence": "3"})
        self.assertTrue(session_id)
        self.assertEqual(4, sequence)

    def testSessionIdWithNoSequenceGivesOne(self):
        self.assertEqual(("abc", 1), self.process({"query.session-id": "abc"}))

    def testIntegerSequenceCountsUp(self):
        self.assertEqual(
            ("abc", 8),
            self.process({"query.session-id": "abc", "query.sequence": 7}))

    def testSessionIdThatIsNotANonEmptyStringIsAbsent(self):
        for value in (123, "", None, ["abc"]):
            session_id, sequence = self.process(
                {"query.session-id": value, "query.sequence": "2"})
            self.assertIsInstance(session_id, str)
            self.assertTrue(session_id)
            self.assertEqual(3, sequence)

    def testSessionIdOfZeroIsKept(self):
        self.assertEqual(
            ("0", 3),
            self.process({"query.session-id": "0", "query.sequence": "2"}))

    def testSequenceThatIsNotWholeDigitsIsAbsent(self):
        for value in ("abc", "", " 5 ", "+5", "-5", "5.0", True, "٣", None):
            self.assertEqual(
                ("abc", 1),
                self.process(
                    {"query.session-id": "abc", "query.sequence": value}),
                repr(value))

    def testLeadingZerosAreAllowed(self):
        self.assertEqual(
            ("abc", 6),
            self.process({"query.session-id": "abc",
                          "query.sequence": "00005"}))

    def testSequenceOfZeroGivesOne(self):
        # "A sequence of 0 gives an output of 1, as an absent one does."
        for value in (0, "0", "000"):
            self.assertEqual(
                ("abc", 1),
                self.process(
                    {"query.session-id": "abc", "query.sequence": value}),
                repr(value))

    def testLargestSequenceCountsUp(self):
        for value in (2147483646, "2147483646"):
            self.assertEqual(
                ("abc", 2147483647),
                self.process(
                    {"query.session-id": "abc", "query.sequence": value}),
                repr(value))

    def testSequenceAboveTheLargestIsAbsent(self):
        # Above 2,147,483,646 adding one would leave a 32 bit integer, so the
        # value is not one the element can use and the output is 1.
        for value in (2147483647, "2147483647", 2 ** 31, "2147483648",
                      10 ** 400, "1" + "0" * 400):
            self.assertEqual(
                ("abc", 1),
                self.process(
                    {"query.session-id": "abc", "query.sequence": value}),
                repr(value))


if __name__ == "__main__":
    unittest.main()

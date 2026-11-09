
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

    def testUnsafeSessionIdIsEmptyInTheElementDataAndTheJson(self):
        flowdata = self.process({"query.session-id": "</script>"})
        self.assertEqual("", flowdata.get("sequence").get("session-id"))
        self.assertEqual("", flowdata.jsonbundler.json["sequence"]["session-id"])
        self.assertNotIn("</script>", flowdata.javascriptbuilder.javascript)

    def testSequencePropertiesAreDescribed(self):
        element = PipelineBuilder({}).build().flow_elements[0]
        self.assertEqual("sequence", element.datakey)
        self.assertEqual(
            {"session-id": {"type": "string"}, "sequence": {"type": "int"}},
            element.get_properties())


if __name__ == "__main__":
    unittest.main()

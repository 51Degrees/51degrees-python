
"""
A Cloud Aspect Engine whose product the key does not include builds with
empty Property metadata, logs the missing product once, and logs nothing
about it on each response, as the Cloud Aspect Engine specification says.
"""

import json
import unittest

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder


class RecordingLogger(Logger):

    def __init__(self):
        super(RecordingLogger, self).__init__("debug")
        self.logged = []

    def log_internal(self, level, log):
        self.logged.append((level, log["message"]))


class FakeCloudRequestEngine(FlowElement):
    """Stands in for the Cloud Request Engine of a key that carries only the
    device product."""

    def __init__(self):
        super(FakeCloudRequestEngine, self).__init__()
        self.datakey = "cloud"
        self.flow_element_properties = {
            "device": {"ismobile": {"name": "IsMobile", "type": "Boolean"}}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"cloud": json.dumps({"device": {"ismobile": True}})}))


def location_engine():
    engine = CloudEngine()
    engine.datakey = "location"
    return engine


class MissingProductTests(unittest.TestCase):

    def build(self):
        logger = RecordingLogger()
        builder = PipelineBuilder({"add_javascript_builder": False,
                                   "use_setheader_properties": False})
        builder.add_logger(logger)
        engine = location_engine()
        pipeline = builder.add(FakeCloudRequestEngine()).add(engine).build()
        self.addCleanup(pipeline.close)
        return pipeline, engine, logger

    def testPipelineBuildsWithEmptyMetadata(self):
        pipeline, engine, logger = self.build()
        self.assertEqual({}, engine.get_properties())

    def testMissingProductIsLoggedOnce(self):
        pipeline, engine, logger = self.build()
        missing = [entry for entry in logger.logged
                   if "location" in entry[1]]
        self.assertEqual(1, len(missing), logger.logged)
        # The specification asks for the warning level.
        self.assertEqual("warning", missing[0][0])

    def testNothingIsLoggedOnEachResponse(self):
        pipeline, engine, logger = self.build()
        before = len(logger.logged)
        for _ in range(3):
            flowdata = pipeline.create_flowdata()
            flowdata.process()
            self.assertEqual(0, len(flowdata.errors))
            self.assertEqual({}, flowdata.get("location").as_dictionary())
        self.assertEqual(before, len(logger.logged), logger.logged)

    def testEngineWithItsProductStillBuildsWithItsProperties(self):
        logger = RecordingLogger()
        builder = PipelineBuilder({"add_javascript_builder": False,
                                   "use_setheader_properties": False})
        builder.add_logger(logger)
        engine = CloudEngine()
        engine.datakey = "device"
        pipeline = builder.add(FakeCloudRequestEngine()).add(engine).build()
        self.addCleanup(pipeline.close)
        self.assertEqual(["ismobile"], list(engine.get_properties()))
        self.assertEqual([], logger.logged)


if __name__ == "__main__":
    unittest.main()

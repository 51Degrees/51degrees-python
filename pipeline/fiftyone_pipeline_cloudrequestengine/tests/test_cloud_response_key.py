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
The Cloud Request Engine's data is read under cloud-response, the Element
Data key the cloud request engine specification gives, and still under the
old key, cloud, which is deprecated. Both keys give the same data.
"""

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.basic_dictionary_cache import \
    BasicDictionaryCache

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.constants import Constants

# The key the specification gives, and the old key.
RESPONSE_KEY = "cloud-response"
OLD_KEY = "cloud"

# The name the raw JSON is read under within the data.
JSON_PROPERTY = "cloud"

# Answers that differ, so a test can tell which key a cloud engine read.
ANSWER_UNDER_RESPONSE_KEY = '{"device":{"value": 2}}'
ANSWER_UNDER_OLD_KEY = '{"device":{"value": 1}}'


class StandInRequestEngine(FlowElement):
    """Stands in for a Cloud Request Engine, giving each answer it is given
    under its own key."""

    def __init__(self, answers):
        super(StandInRequestEngine, self).__init__()
        self.datakey = OLD_KEY
        self.answers = answers
        self.flow_element_properties = {
            "device": {"value": {"name": "value", "type": "Int32"}}}

    def process_internal(self, flowdata):
        for key, answer in self.answers.items():
            flowdata.data[key] = ElementDataDictionary(
                self, {JSON_PROPERTY: answer})


class CloudResponseKeyTests(CloudRequestEngineTestsBase):

    def pipeline(self, cache=None):
        """A pipeline holding a Cloud Request Engine, with the cache given
        if there is one."""

        engine = CloudRequestEngine({
            "resource_key": Constants.resourceKey,
            "http_client": self.mock_http()})
        if cache is not None:
            engine.set_cache(cache)
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}).add(engine).build()
        self.addCleanup(pipeline.close)
        return pipeline

    @staticmethod
    def process(pipeline):
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", Constants.userAgent)
        data.process()
        return data

    def read_device_value(self, answers):
        """The value a cloud engine reads from a stand-in request engine
        that gives the answers given."""

        device = CloudEngine()
        device.datakey = "device"
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False}) \
            .add(StandInRequestEngine(answers)).add(device).build()
        self.addCleanup(pipeline.close)
        data = pipeline.create_flowdata()
        data.process()
        return data.get("device").get("value").value()

    def assert_both_keys_give_the_same_data(self, data):
        """Each way of reading under the old key gives the object read under
        cloud-response."""

        response = data.get(RESPONSE_KEY)
        self.assertEqual(Constants.jsonResponse, response.get(JSON_PROPERTY))
        self.assertIs(response, data[RESPONSE_KEY])
        self.assertIs(response, data.get(OLD_KEY))
        self.assertIs(response, data[OLD_KEY])
        self.assertIs(response, data.cloud)

    def test_both_keys_give_the_same_data(self):
        self.assert_both_keys_give_the_same_data(
            self.process(self.pipeline()))

    def test_both_keys_give_the_same_data_from_the_cache(self):
        pipeline = self.pipeline(cache=BasicDictionaryCache())
        self.process(pipeline)

        # The second request with the same evidence is answered from the
        # cache, so it sends no request for data.
        data = self.process(pipeline)

        sent = pipeline.get_element(OLD_KEY).http_client.requests
        self.assertEqual(
            1, len([request for request in sent if ".json" in request[1]]))
        self.assert_both_keys_give_the_same_data(data)

    def test_a_cloud_engine_reads_the_data_under_cloud_response(self):
        self.assertEqual(2, self.read_device_value({
            OLD_KEY: ANSWER_UNDER_OLD_KEY,
            RESPONSE_KEY: ANSWER_UNDER_RESPONSE_KEY}))

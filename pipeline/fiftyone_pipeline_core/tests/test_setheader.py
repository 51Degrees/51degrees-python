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

import requests_mock
import requests
import unittest
from parameterized import parameterized

from fiftyone_pipeline_core.messages import Messages
from fiftyone_pipeline_core.web import *
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_core.setheaderelement import SetHeaderElement

from .classes.testpipeline import TestPipeline
from .classes.constants import Constants


unknown_value = AspectPropertyValue(value = Constants.UNKNOWN)
browser_value = AspectPropertyValue(value = Constants.ACCEPTCH_BROWSER_VALUE)
platform_value = AspectPropertyValue(value = Constants.ACCEPTCH_PLATFORM_VALUE)
hardware_value = AspectPropertyValue(value = Constants.ACCEPTCH_HARDWARE_VALUE)

setHeader_properties_dict = {'device': ['SetHeaderBrowserAccept-CH', 'SetHeaderHardwareAccept-CH', 'SetHeaderPlatformAccept-CH']}


class SetHeaderUACHTests(unittest.TestCase):
    # Test response header value to be set for UACH
    @parameterized.expand([
        ({"device" : { "setheaderbrowseraccept-ch": unknown_value}}, ""),
        ({"device" : { "setheaderbrowseraccept-ch": browser_value}}, "SEC-CH-UA,SEC-CH-UA-Full-Version"),
        ({"device" : { "setheaderplatformaccept-ch": platform_value, "setheaderhardwareaccept-ch": hardware_value}}, "SEC-CH-UA-Model,SEC-CH-UA-Mobile,SEC-CH-UA-Arch,SEC-CH-UA-Platform,SEC-CH-UA-Platform-Version"),
        ({"device" : { "setheaderhardwareaccept-ch": hardware_value}}, "SEC-CH-UA-Model,SEC-CH-UA-Mobile,SEC-CH-UA-Arch"),
        ({"device" : { "setheaderbrowseraccept-ch": browser_value, "setheaderplatformaccept-ch": platform_value, "setheaderhardwareaccept-ch": hardware_value}}, "SEC-CH-UA,SEC-CH-UA-Full-Version,SEC-CH-UA-Model,SEC-CH-UA-Mobile,SEC-CH-UA-Arch,SEC-CH-UA-Platform,SEC-CH-UA-Platform-Version")
    ])
    def test_get_response_header_value(self, device, expected_value):
        testPipeline = TestPipeline()
        setHeaderElement = SetHeaderElement()
        # A FlowData that has not been processed, because a finished one
        # takes no more ElementData.
        flowdata = testPipeline.pipeline.create_flowdata()
        flowdata.data = device
        actual_value = setHeaderElement.get_response_header_value(flowdata, setHeader_properties_dict)
        self.assertEqual(expected_value, actual_value[Constants.ACCEPTCH_HEADER])

    # Test set response header function with empty string and with a value.
    # UACH response header should not be set in empty string case.

    @parameterized.expand([
        ({"set-headers" : {"responseheaderdictionary" : {"Accept-CH": ""}}}, False),
        ({"set-headers" : {"responseheaderdictionary" : {"Accept-CH": "SEC-CH-UA,SEC-CH-UA-Full-Version"}}}, True)
        ])
    def test_set_response_header(self, data, expected_value):
        adapter = requests_mock.Adapter()
        session = requests.Session()
        session.mount('mock', adapter) 
        adapter.register_uri('GET',
                        'mock://test.com/3',
                        headers={},
                        status_code=200)
        response = session.get('mock://test.com/3')

        testPipeline = TestPipeline()
        # A FlowData that has not been processed, because a finished one
        # takes no more ElementData.
        flowdata = testPipeline.pipeline.create_flowdata()
        flowdata.data = data

        response = set_response_header(flowdata, response)
        self.assertEqual(expected_value, Constants.ACCEPTCH_HEADER in response.headers)

    # Test get response header function for valid formats. The name is
    # SetHeader[Identifier][HeaderName], and the identifier has no upper-case
    # characters after its first character, which may be either case.
    @parameterized.expand([
        ("SetHeaderBrowserAccept-CH", "Accept-CH"),
        ("SetHeaderHardwareAccept-CH", "Accept-CH"),
        ("SetHeaderPlatformAccept-CH", "Accept-CH"),
        ("SetHeaderBrowserCritical-CH", "Critical-CH"),
        ("SetHeaderUnknownAccept-CH", "Accept-CH"),
        ("SetHeaderbrowserAccept-CH", "Accept-CH"),
        # The header name holds the identifier, which must be kept.
        ("SetHeaderAcceptAccept-CH", "Accept-CH")
        ])
    def test_get_response_header_name(self, property_key, expected_value):
        setHeaderElement = SetHeaderElement()
        actual_value = setHeaderElement.get_response_header_name(property_key)
        self.assertEqual(expected_value, actual_value)

    # Test get response header function raises exception
    # for invalid property formats.
    @parameterized.expand([
    ("TestBrowserAccept-CH", Messages.PROPERTY_NOT_SET_HEADER),
    ("SetHeaderBrowseraccept-ch", Messages.WRONG_PROPERTY_FORMAT),
    ("SetHeaderbrowser", Messages.WRONG_PROPERTY_FORMAT),
    ("SetHeaderBrowser", Messages.WRONG_PROPERTY_FORMAT),
    ("SetHeader", Messages.WRONG_PROPERTY_FORMAT)
    ])
    def test_get_response_header_name_error(
            self, property_value, expected_message):

        setHeaderElement = SetHeaderElement()
        with self.assertRaises(Exception) as caught:
            setHeaderElement.get_response_header_name(property_value)

        self.assertEqual(
            expected_message.format(property_value), str(caught.exception))

    # Only a property whose name starts with SetHeader is for a response
    # header, so a name that holds SetHeader later on is left alone.
    def test_get_setheader_properties_pipeline_needs_the_prefix(self):

        class Element(object):
            datakey = "device"

            def get_properties(self):
                return {
                    "setheaderbrowseraccept-ch": {
                        "name": "SetHeaderBrowserAccept-CH"},
                    "notsetheaderbrowseraccept-ch": {
                        "name": "NotSetHeaderBrowserAccept-CH"}}

        class Pipeline(object):
            flow_elements = [Element()]

        self.assertEqual(
            {"device": ["SetHeaderBrowserAccept-CH"]},
            SetHeaderElement().get_setheader_properties_pipeline(Pipeline()))


# An element with one property for a response header, whose value is the
# header's value.
class HeaderSourceElement(FlowElement):

    def __init__(self, datakey, property_name, value):
        super(HeaderSourceElement, self).__init__()
        self.datakey = datakey
        self.property_name = property_name
        self.value = value
        self.properties = {
            property_name: {"name": property_name, "type": "string"}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self,
            {self.property_name: AspectPropertyValue(value=self.value)}))


def response_headers(pipeline):
    flowdata = pipeline.create_flowdata()
    flowdata.process()
    return flowdata["set-headers"]["responseheaderdictionary"]


BROWSER_HEADERS = {"Accept-CH": Constants.ACCEPTCH_BROWSER_VALUE}
PLATFORM_HEADERS = {"Critical-CH": Constants.ACCEPTCH_PLATFORM_VALUE}


# The multi-pipeline elements specification says an element that keeps
# state for the Pipeline it is in keeps that state for each Pipeline it is
# added to. One Set Headers Element is shared by two Pipelines whose other
# elements give different SetHeader properties.
class SetHeaderMultiPipelineTests(unittest.TestCase):

    def setUp(self):
        self.set_headers = set_headers = SetHeaderElement()
        # The Pipelines share an element, so neither closes its elements.
        self.pipelines = {
            "browser": Pipeline(
                [HeaderSourceElement(
                    "browser", "SetHeaderBrowserAccept-CH",
                    Constants.ACCEPTCH_BROWSER_VALUE),
                 set_headers],
                auto_close_elements=False),
            "platform": Pipeline(
                [HeaderSourceElement(
                    "platform", "SetHeaderPlatformCritical-CH",
                    Constants.ACCEPTCH_PLATFORM_VALUE),
                 set_headers],
                auto_close_elements=False)}
        self.expected = {
            "browser": BROWSER_HEADERS, "platform": PLATFORM_HEADERS}

    # Each Pipeline gives the headers of its own elements, whichever
    # processes first, and keeps doing so after the other has processed.
    @parameterized.expand([
        ("browser_first", ["browser", "platform"]),
        ("platform_first", ["platform", "browser"])])
    def test_each_pipeline_gives_its_own_headers(self, _, order):
        for name in order + order:
            self.assertEqual(
                self.expected[name], response_headers(self.pipelines[name]),
                name)

    # setheader_properties holds the SetHeader properties of the first
    # Pipeline that processed, as a dict of data key to property names, for
    # code that reads it.
    def test_setheader_properties_holds_the_first_pipelines_properties(self):
        response_headers(self.pipelines["browser"])
        response_headers(self.pipelines["platform"])
        self.assertEqual(
            {"browser": ["SetHeaderBrowserAccept-CH"]},
            self.set_headers.setheader_properties)

    def test_one_pipeline_gives_the_same_headers_on_every_request(self):
        for _ in range(3):
            self.assertEqual(
                BROWSER_HEADERS, response_headers(self.pipelines["browser"]))

    # A cloud engine has no properties until the cloud service has
    # answered, so a Pipeline whose SetHeader properties are not known on
    # its first request gives the headers once they are.
    def test_headers_are_given_once_the_properties_are_known(self):
        source = HeaderSourceElement(
            "browser", "SetHeaderBrowserAccept-CH",
            Constants.ACCEPTCH_BROWSER_VALUE)
        properties = source.properties
        source.properties = {}
        pipeline = Pipeline([source, SetHeaderElement()])
        self.assertEqual({}, response_headers(pipeline))
        source.properties = properties
        self.assertEqual(BROWSER_HEADERS, response_headers(pipeline))

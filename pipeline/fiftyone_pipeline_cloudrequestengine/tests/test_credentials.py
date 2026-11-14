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

import warnings

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.constants import Constants
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .classes.accepteverykeyelement import AcceptEveryKeyElement
from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase

RESOURCE_KEY = "resource_key"
LICENSE_KEY = "a-licence-key"
REQUESTED = ["device.ismobile", "device.istablet"]


class TestCredentials(CloudRequestEngineTestsBase):
    """!
    Checks every combination of resource key, licence key and requested
    properties in the Credentials table of the cloud request engine
    specification, and where each credential travels in the requests the
    engine makes.
    """

    def process(self, engine):
        """
        Run one flow data through a pipeline holding the engine, and give
        back the requests the mock client saw.
        """

        pipeline = PipelineBuilder().add(engine).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", "iPhone")
        data.process()
        return engine.http_client.requests

    def data_request(self, requests):
        """The last request, being the one for data."""

        return requests[-1]

    def test_resource_key_alone_is_accepted(self):
        """
        Row one of the table. The resource key names the route and the
        body carries the resource key and the evidence, with no licence
        key and no list of properties.
        """

        engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "http_client": self.mock_http(),
        })

        request_type, url, content = self.data_request(
            self.process(engine))

        self.assertEqual("POST", request_type)
        self.assertTrue(url.endswith(RESOURCE_KEY + ".json?"), url)
        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertNotIn(Constants.LICENSE_PARAMETER, content)
        self.assertNotIn(Constants.VALUES_PARAMETER, content)
        self.assertEqual("iPhone", content["User-Agent"])

    def test_resource_key_with_licence_key_is_accepted(self):
        """
        Row two of the table. With no list the answer holds what the
        resource key carries and the licence key adds no property, so the
        licence key travels in the body of the data request and of the
        accessible properties request, and no list of properties is sent.
        """

        engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "license_key": LICENSE_KEY,
            "http_client": self.mock_http(),
        })

        requests = self.process(engine)

        properties_requests = [
            request for request in requests
            if "accessibleProperties" in request[1]]
        self.assertEqual(1, len(properties_requests))
        request_type, url, content = properties_requests[0]
        self.assertEqual("POST", request_type)
        self.assertNotIn(LICENSE_KEY, url)
        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])

        request_type, url, content = self.data_request(requests)
        self.assertTrue(url.endswith(RESOURCE_KEY + ".json?"), url)
        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertNotIn(Constants.VALUES_PARAMETER, content)

    def test_licence_key_with_properties_is_accepted(self):
        """
        Row three of the table. With no resource key the data request goes
        to the route that takes none, and the body names the licence key
        and the properties wanted. The licence key never appears in a URL.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })

        requests = self.process(engine)

        for request_type, url, content in requests:
            self.assertNotIn(LICENSE_KEY, url)

        request_type, url, content = self.data_request(requests)
        self.assertEqual("POST", request_type)
        self.assertEqual(Constants.BASE_URL_DEFAULT + "json", url)
        self.assertNotIn(Constants.RESOURCE_PARAMETER, content)
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertEqual(
            "device.ismobile,device.istablet",
            content[Constants.VALUES_PARAMETER])

    def test_licence_key_discovers_properties_with_the_key_in_the_body(self):
        """
        The accessible properties request made with a licence key alone
        posts the key in the body, and the engine builds with the metadata
        the service answers.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })

        self.assertIn("device", engine.flow_element_properties)

        # The engine also asks for the evidence keys when it is built, so
        # the request for the properties is found by its address.
        properties_requests = [
            request for request in engine.http_client.requests
            if "accessibleProperties" in request[1]]
        self.assertEqual(1, len(properties_requests))
        request_type, url, content = properties_requests[0]
        self.assertEqual("POST", request_type)
        self.assertEqual(
            Constants.BASE_URL_DEFAULT + "accessibleProperties", url)
        self.assertEqual({Constants.LICENSE_PARAMETER: LICENSE_KEY}, content)

    def test_licence_key_without_properties_is_refused(self):
        """
        Row four of the table. The service answers 400 to every such
        request, so the engine refuses to build and says why.
        """

        with self.assertRaises(ValueError) as context:
            CloudRequestEngine({
                "license_key": LICENSE_KEY,
                "http_client": self.mock_http(),
            })

        self.assertIn("400", str(context.exception))
        self.assertIn("requested_properties", str(context.exception))

    def test_properties_with_resource_key_are_sent(self):
        """
        A list beside a resource key, with and without a licence key. The
        service adds the listed properties to those the resource key
        carries, so the engine builds and sends the list as values, with
        the licence key in the body where there is one.
        """

        for license_key in ("", LICENSE_KEY):
            engine = CloudRequestEngine({
                "resource_key": RESOURCE_KEY,
                "license_key": license_key,
                "requested_properties": REQUESTED,
                "http_client": self.mock_http(),
            })

            requests = self.process(engine)

            for request_type, url, content in requests:
                self.assertNotIn(LICENSE_KEY, url)

            request_type, url, content = self.data_request(requests)
            self.assertTrue(url.endswith(RESOURCE_KEY + ".json?"), url)
            self.assertEqual(
                RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
            self.assertEqual(
                "device.ismobile,device.istablet",
                content[Constants.VALUES_PARAMETER])
            if license_key == "":
                self.assertNotIn(Constants.LICENSE_PARAMETER, content)
            else:
                self.assertEqual(
                    LICENSE_KEY, content[Constants.LICENSE_PARAMETER])

    def test_no_credential_is_refused(self):
        """
        Row six of the table, with and without a list of properties. There
        is nothing to authenticate with.
        """

        for requested_properties in ([], REQUESTED):
            with self.assertRaises(ValueError) as context:
                CloudRequestEngine({
                    "requested_properties": requested_properties,
                    "http_client": self.mock_http(),
                })

            self.assertIn("401", str(context.exception))

    def test_whitespace_counts_as_absent(self):
        """
        A credential read from the environment often carries a trailing
        newline, and a value that is only whitespace is a mistake rather
        than a key. Each is trimmed, and an empty one is treated as absent
        in the rules, so whitespace alone cannot satisfy them.
        """

        engine = CloudRequestEngine({
            "resource_key": " " + RESOURCE_KEY + "\n",
            "license_key": "   ",
            "requested_properties": [" ", ""],
            "http_client": self.mock_http(),
        })

        self.assertEqual(RESOURCE_KEY, engine.resource_key)
        self.assertEqual("", engine.license_key)
        self.assertEqual([], engine.requested_properties)

        with self.assertRaises(ValueError):
            CloudRequestEngine({
                "license_key": "\t",
                "requested_properties": REQUESTED,
                "http_client": self.mock_http(),
            })

    def test_properties_may_be_one_comma_separated_string(self):
        """
        A configuration file holds the list as one string, so that form is
        accepted and each name is trimmed and lower-cased to match the
        case the service answers in.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": " Device.IsMobile , device.IsTablet,",
            "http_client": self.mock_http(),
        })

        self.assertEqual(REQUESTED, engine.requested_properties)

    def test_reserved_evidence_is_left_out_of_the_body(self):
        """
        The service advertises values, resource and license among its
        accepted evidence keys. Evidence carrying one of them would sit in
        the body beside the engine's own credentials, so it is dropped
        whatever its prefix.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })

        # The stand-in service lists query.User-Agent alone, so an element
        # that accepts every key keeps this evidence for the engine, which
        # leaves it out whatever reaches it.
        pipeline = PipelineBuilder().add(AcceptEveryKeyElement()) \
            .add(engine).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.license", "another-key")
        data.evidence.add("header.resource", "another-key")
        data.evidence.add("cookie.values", "device.iscrawler")
        data.evidence.add("query.User-Agent", "iPhone")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data.process()

        request_type, url, content = engine.http_client.requests[-1]
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertNotIn(Constants.RESOURCE_PARAMETER, content)
        self.assertEqual(
            "device.ismobile,device.istablet",
            content[Constants.VALUES_PARAMETER])
        self.assertEqual("iPhone", content["User-Agent"])

        # Each piece of evidence left out is named once, without its
        # value, as the value may be a credential.
        messages = [
            str(warning.message) for warning in caught
            if "is not sent" in str(warning.message)]
        self.assertEqual(3, len(messages), messages)
        for evidence_key in (
                "query.license", "header.resource", "cookie.values"):
            self.assertTrue(
                any(evidence_key in message for message in messages),
                evidence_key)
        for message in messages:
            self.assertNotIn("another-key", message)

    def send_with_reserved_evidence(self, settings):
        """
        Process one flow data holding evidence named resource, license, licence
        and values in mixed case under each prefix, with other evidence beside
        it, and give back the body of the data request.
        """

        settings["http_client"] = self.mock_http()
        engine = CloudRequestEngine(settings)
        # The stand-in service lists query.User-Agent alone, so an element
        # that accepts every key keeps the other evidence for the engine.
        pipeline = PipelineBuilder().add(AcceptEveryKeyElement()) \
            .add(engine).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.Resource", "evidence_resource")
        data.evidence.add("query.LICENSE", "evidence_license")
        data.evidence.add("query.Licence", "evidence_licence")
        data.evidence.add("query.Values", "evidence_values")
        data.evidence.add("header.resource", "header_resource")
        data.evidence.add("cookie.License", "cookie_license")
        data.evidence.add("query.other", "query_other")
        data.evidence.add("header.other", "header_other")
        data.evidence.add("cookie.cookie-only", "cookie_only")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data.process()

        return engine.http_client.requests[-1][2]

    def assert_other_evidence_sent(self, content):
        self.assertEqual("query_other", content["other"])
        self.assertEqual("cookie_only", content["cookie-only"])
        for value in content.values():
            self.assertNotIn("evidence_", str(value))
            self.assertNotIn("header_resource", str(value))
            self.assertNotIn("cookie_license", str(value))

    def test_evidence_never_supplies_resource_or_license(self):
        """
        With a Resource Key and a License Key configured, the body carries
        those two and none of the evidence named resource, license or
        values, in any case and under any prefix.
        """

        content = self.send_with_reserved_evidence({
            "resource_key": RESOURCE_KEY,
            "license_key": LICENSE_KEY,
        })

        self.assertEqual(RESOURCE_KEY, content[Constants.RESOURCE_PARAMETER])
        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertNotIn(Constants.VALUES_PARAMETER, content)
        self.assertEqual(
            [], [name for name in content if name.lower() in (
                "resource", "license", "licence", "values") and name not in (
                Constants.RESOURCE_PARAMETER, Constants.LICENSE_PARAMETER)])
        self.assert_other_evidence_sent(content)

    def test_evidence_never_supplies_values(self):
        """
        With a License Key and Requested Properties configured, the body
        carries the configured list as values and the License Key as
        license, and no resource, whatever the evidence holds.
        """

        content = self.send_with_reserved_evidence({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
        })

        self.assertEqual(LICENSE_KEY, content[Constants.LICENSE_PARAMETER])
        self.assertEqual(
            "device.ismobile,device.istablet",
            content[Constants.VALUES_PARAMETER])
        self.assertNotIn(Constants.RESOURCE_PARAMETER, content)
        self.assertEqual(
            [], [name for name in content if name.lower() in (
                "resource", "license", "licence", "values") and name not in (
                Constants.LICENSE_PARAMETER, Constants.VALUES_PARAMETER)])
        self.assert_other_evidence_sent(content)

    def test_evidence_no_element_accepts_is_sent(self):
        """
        The engine sends every evidence value in the flow data apart from
        the reserved names, so a header and a cookie that no element in a
        default pipeline accepts are sent as well.
        """
        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })

        pipeline = PipelineBuilder().add(engine).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", "iPhone")
        data.evidence.add("header.x-test", "a header")
        data.evidence.add("cookie.other", "a cookie")
        data.process()

        request_type, url, content = engine.http_client.requests[-1]
        self.assertEqual("a header", content["x-test"])
        self.assertEqual("a cookie", content["other"])
        self.assertEqual("iPhone", content["User-Agent"])

    def test_properties_added_later_are_normalised_and_sent(self):
        """
        A caller may add to the list after the engine is built, once the
        accessible properties say which client-side properties the key
        carries. The names added are trimmed and lower-cased as the
        constructor's are, so they match the answer, and they are sent
        beside a resource key as well as beside a licence key alone.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(),
        })

        engine.add_requested_properties([" Device.IsCrawler ", ""])
        engine.add_requested_properties("device.hardwarename, ")

        self.assertEqual(
            REQUESTED + ["device.iscrawler", "device.hardwarename"],
            engine.requested_properties)

        request_type, url, content = self.data_request(
            self.process(engine))
        self.assertEqual(
            ",".join(engine.requested_properties),
            content[Constants.VALUES_PARAMETER])

        engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "http_client": self.mock_http(),
        })

        engine.add_requested_properties(REQUESTED)

        request_type, url, content = self.data_request(
            self.process(engine))
        self.assertEqual(
            "device.ismobile,device.istablet",
            content[Constants.VALUES_PARAMETER])

    def test_properties_the_answer_leaves_out_are_reported_once(self):
        """
        The service drops a property the licence key does not cover
        without naming it. The engine compares the list it sent with the
        answer, warns once naming the missing property, and does not warn
        again on the next request. A property present but null counts as
        answered, because its nullreason explains it.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": [
                "Device.IsMobile", "device.istablet", "device.iscrawler"],
            "http_client": self.mock_http(license_json_response=(
                '{"device":{"ismobile":true,"istablet":null,'
                '"istabletnullreason":"No value on this request"}}')),
        })

        pipeline = PipelineBuilder().add(engine).build()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for _ in range(2):
                data = pipeline.create_flowdata()
                data.evidence.add("query.User-Agent", "iPhone")
                data.process()

        messages = [
            str(warning.message) for warning in caught
            if "not covered" in str(warning.message)]
        self.assertEqual(1, len(messages), messages)
        self.assertIn("not covered by the keys in use", messages[0])
        self.assertIn("device.iscrawler", messages[0])
        self.assertNotIn("device.istablet", messages[0])
        self.assertNotIn("device.ismobile", messages[0])

    def test_a_name_left_out_beside_a_resource_key_alone_is_not_a_property(
            self):
        """
        With a resource key, a list and no licence key, a property no
        licence grants comes back as null with its nullreason, so a name the
        answer leaves out is not a property at all. The engine says so,
        once, and does not name a licence key that was never given.
        """

        engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "requested_properties": ["device.value", "device.notaproperty"],
            "http_client": self.mock_http(),
        })

        pipeline = PipelineBuilder().add(engine).build()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for _ in range(2):
                data = pipeline.create_flowdata()
                data.evidence.add("query.User-Agent", "iPhone")
                data.process()

        messages = [
            str(warning.message) for warning in caught
            if "device.notaproperty" in str(warning.message)]
        self.assertEqual(1, len(messages), messages)
        self.assertIn(
            "Every property is answered, with a reason when it has no "
            "value, so these names are not properties", messages[0])
        self.assertIn("Check the spelling of each one", messages[0])
        self.assertNotIn("licence key", messages[0])
        self.assertNotIn("device.value", messages[0])

    def test_an_answer_that_is_not_an_object_does_not_fail_the_request(self):
        """
        The report compares the answer with the list, and an answer that
        parses as JSON but is not an object has nothing to compare. It
        must not fail the request, because the request itself succeeded,
        so the engine leaves the answer alone and says nothing.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": REQUESTED,
            "http_client": self.mock_http(
                license_json_response='["device", "ismobile"]'),
        })

        pipeline = PipelineBuilder().add(engine).build()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data = pipeline.create_flowdata()
            data.evidence.add("query.User-Agent", "iPhone")
            data.process()

        self.assertEqual(
            [], [str(warning.message) for warning in caught
                 if "did not return" in str(warning.message)])

    def test_no_report_when_every_property_came_back(self):
        """
        An answer carrying every requested property raises no warning, and
        an engine on a resource key sends no list so there is nothing to
        compare.
        """

        for settings in (
                {"license_key": LICENSE_KEY,
                 "requested_properties": ["device.value"]},
                {"resource_key": RESOURCE_KEY}):
            settings["http_client"] = self.mock_http()
            engine = CloudRequestEngine(settings)
            pipeline = PipelineBuilder().add(engine).build()

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                data = pipeline.create_flowdata()
                data.evidence.add("query.User-Agent", "iPhone")
                data.process()

            self.assertEqual([], [
                str(warning.message) for warning in caught
                if "not covered" in str(warning.message)])

    def test_missing_property_message_names_both_causes(self):
        """
        With a licence key the accessible properties list everything the
        licence entitles, so a property can be listed as carried and still
        be absent from an answer because it was not requested. The message
        for a property that is not in the data says so, and names the
        element it looked in rather than assuming device.
        """

        engine = CloudRequestEngine({
            "license_key": LICENSE_KEY,
            "requested_properties": ["device.value"],
            "http_client": self.mock_http(),
        })
        device = CloudEngine()
        device.datakey = "device"

        pipeline = PipelineBuilder().add(engine).add(device).build()
        data = pipeline.create_flowdata()
        data.evidence.add("query.User-Agent", "iPhone")
        data.process()

        with self.assertRaises(Exception) as context:
            data.device.get("other")

        message = str(context.exception)
        self.assertIn("Property other not found", message)
        self.assertIn("requested_properties", message)
        self.assertIn("under device are value", message)
        self.assertNotIn("your resource key", message)

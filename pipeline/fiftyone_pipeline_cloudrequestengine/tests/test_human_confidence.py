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
The Cloud Request Engine redeems a sealed Human Confidence value through
its JSON call, and a consumer reads HumanConfidence and
HumanConfidenceSource, as the Human Confidence page of the specification
says. Each test below follows one item of that page's "Required tests".
"""

import json
import warnings

import requests

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.humanconfidence import \
    HumanConfidenceChallenges
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.aspectdata_dictionary import \
    AspectDataDictionary
from fiftyone_pipeline_engines.basic_dictionary_cache import \
    BasicDictionaryCache

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.mockrequestclient import MockRequestClient

SEALED = "sealed-0f3a9c27d4b8e615a2c7"
LICENSE_KEY = "license-key-8d2e61b7c3f9"
OTHER_CHALLENGE = "challenge-from-the-request-5b1d"


class Answer:
    """What the stand-in cloud service answers the JSON call with: a
    status and text, or an error it raises."""

    def __init__(self, text=None, status=200, raises=None):
        self.text = text
        self.status = status
        self.raises = raises


def level_answer(level):
    """A JSON call answer whose derived section holds the level given."""

    return Answer(json.dumps({"derived": {"humanconfidence": level}}))


class StandInCloud(MockRequestClient):
    """Answers discovery as the mock client does, and the JSON call with
    the Answer given. Keeps the content of every JSON call."""

    def __init__(self, answer, discovery_fails=False):
        super(StandInCloud, self).__init__()
        self.answer = answer
        self.discovery_fails = discovery_fails
        self.json_calls = []

    def request(self, type, url, content, originHeader):
        discovery = ("accessibleProperties" in url
                     or "evidencekeys" in url)
        if discovery and self.discovery_fails:
            raise requests.ConnectionError("discovery failed")
        response = super(StandInCloud, self).request(
            type, url, content, originHeader)
        if discovery:
            return response
        self.json_calls.append(dict(content or {}))
        if self.answer.raises is not None:
            raise self.answer.raises
        response.status_code = self.answer.status
        response.text = self.answer.text
        response.content = (self.answer.text or "").encode("utf-8")
        response.url = url
        response.headers = {}
        return response


class ListLogger(Logger):
    """Keeps every message the pipeline logs."""

    def __init__(self):
        super(ListLogger, self).__init__(min_level="debug")
        self.messages = []

    def log_internal(self, level, log):
        self.messages.append(str(log))


def derived_engine():
    """The cloud engine that reads the derived section of the answer,
    where HumanConfidence and HumanConfidenceSource are."""

    engine = CloudEngine()
    engine.datakey = "derived"
    return engine


class TestHumanConfidence(CloudRequestEngineTestsBase):

    def build(self, answer, license_key=LICENSE_KEY, discovery_fails=False,
              cache=None, challenges=None, suppress=True):
        """A pipeline of a Cloud Request Engine and a cloud engine for derived,
        with the stand-in cloud answering the JSON call."""

        self.cloud = StandInCloud(answer, discovery_fails)
        settings = {"resource_key": "resource_key",
                    "http_client": self.cloud}
        if license_key:
            settings["license_key"] = license_key
        if challenges is not None:
            settings["human_confidence_challenges"] = challenges
        with warnings.catch_warnings(record=True) as self.build_warnings:
            warnings.simplefilter("always")
            self.engine = CloudRequestEngine(settings)
        if cache is not None:
            self.engine.set_cache(cache)
        self.logger = ListLogger()
        self.pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False,
            "suppress_process_exceptions": suppress}).add(
                self.engine).add(derived_engine()).add_logger(
                    self.logger).build()
        self.addCleanup(self.pipeline.close)
        return self.engine

    def page(self):
        """The values a page is given, as the engine gives them."""

        return self.engine.human_confidence_page_values()

    def process(self, sealed=SEALED, page=None, evidence=None):
        """One request that carries the sealed value and the page value
        given. Gives the FlowData and the warnings it gave."""

        if page is None:
            page = self.page()["humanconfidencepage"]
        data = self.pipeline.create_flowdata()
        data.evidence.add("header.user-agent", "Mozilla/5.0")
        if sealed is not None:
            data.evidence.add("query.humanconfidence", sealed)
        if page:
            data.evidence.add("query.humanconfidencepage", page)
        for key, value in (evidence or {}).items():
            data.evidence.add(key, value)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            data.process()
        self.process_warnings = caught
        return data

    def read(self, data):
        """HumanConfidence and HumanConfidenceSource, as a consumer reads
        them."""

        derived = data.get("derived")
        return (derived.get("humanconfidence").value(),
                derived.get("humanconfidencesource").value())

    def assert_low_and_active(self, data, errors=("cloud",)):
        self.assertEqual(("Low", "Active"), self.read(data))
        # The read adds no error of its own. An error of the call is the
        # Cloud Request Engine's, and only that.
        self.assertTrue(set(data.errors) <= set(errors), data.errors)
        answer = json.loads(data.get("cloud-response").get("cloud"))
        self.assertEqual("Low", answer["derived"]["humanconfidence"])
        self.assertEqual("Active", answer["derived"]["humanconfidencesource"])

    # A sealed value that redeems gives the level in the response as
    # HumanConfidence, with HumanConfidenceSource Active.

    def test_a_sealed_value_that_redeems_gives_its_level_and_active(self):
        for level in ("High", "Medium", "Low"):
            with self.subTest(level=level):
                self.build(level_answer(level))
                data = self.process()
                self.assertEqual((level, "Active"), self.read(data))
                self.assertEqual({}, data.errors)

    def test_the_call_sends_the_sealed_value_challenge_and_license_key(self):
        self.build(level_answer("High"))
        page = self.page()
        self.process(page=page["humanconfidencepage"])
        self.assertEqual(1, len(self.cloud.json_calls))
        sent = self.cloud.json_calls[0]
        self.assertEqual(SEALED, sent["humanconfidence"])
        self.assertEqual(page["challenge"], sent["challenge"])
        self.assertEqual(LICENSE_KEY, sent["license"])
        self.assertIn("derived.humanconfidence", sent["values"].split(","))
        self.assertNotIn("humanconfidencepage",
                         [name.lower() for name in sent])

    def test_a_source_in_the_answer_does_not_change_active(self):
        self.build(Answer(json.dumps({"derived": {
            "humanconfidence": "Medium",
            "humanconfidencesource": "Passive"}})))
        self.assertEqual(("Medium", "Active"), self.read(self.process()))

    # Each case where the sealed value is not redeemed gives Low and
    # Active, and the read adds no error of its own.

    def test_no_license_key_gives_low_and_active(self):
        self.build(level_answer("High"), license_key=None)
        data = self.process()
        self.assert_low_and_active(data)
        sent = self.cloud.json_calls[0]
        self.assertNotIn("humanconfidence", sent)
        self.assertNotIn("challenge", sent)

    def test_no_request_for_the_flow_data_gives_low_and_active(self):
        self.build(level_answer("High"), discovery_fails=True)
        data = self.process()
        self.assertEqual([], self.cloud.json_calls)
        # Without the evidence keys the pipeline cannot filter the
        # evidence either, which it records as its own "global" error.
        self.assert_low_and_active(data, errors=("cloud", "global"))
        self.assertIn("cloud", data.errors)

    def test_a_failed_call_gives_low_and_active(self):
        answers = {
            "status 500": Answer(json.dumps({"errors": ["failed"]}), 500),
            "status 400": Answer(json.dumps({"errors": ["refused"]}), 400),
            "not JSON": Answer("<html>Bad gateway</html>", 502),
            "connection": Answer(raises=requests.ConnectionError("down")),
            "timeout": Answer(raises=requests.Timeout("timed out")),
        }
        for case, answer in answers.items():
            with self.subTest(case=case):
                self.build(answer)
                data = self.process()
                self.assert_low_and_active(data)
                self.assertIn("cloud", data.errors)

    def test_a_failed_call_is_still_raised_without_suppression(self):
        self.build(Answer(raises=requests.Timeout("timed out")),
                   suppress=False)
        with self.assertRaises(requests.Timeout):
            self.process()

    def test_an_answer_without_a_level_gives_low_and_active(self):
        answers = {
            "no derived": {"device": {"ismobile": True}},
            "no humanconfidence": {"derived": {"other": "x"}},
            "null": {"derived": {"humanconfidence": None,
                                 "humanconfidencenullreason": "none"}},
            "Unknown": {"derived": {"humanconfidence": "Unknown"}},
            "other word": {"derived": {"humanconfidence": "Maybe"}},
            "lower case": {"derived": {"humanconfidence": "high"}},
            "a number": {"derived": {"humanconfidence": 1}},
            "derived not an object": {"derived": "High"},
        }
        for case, answer in answers.items():
            with self.subTest(case=case):
                self.build(Answer(json.dumps(answer)))
                self.assert_low_and_active(self.process())

    def test_a_page_without_a_kept_challenge_gives_low_and_active(self):
        cases = {"no page value": "",
                 "a page value never given": "0" * 32}
        for case, page in cases.items():
            with self.subTest(case=case):
                self.build(level_answer("High"))
                data = self.process(page=page)
                self.assert_low_and_active(data)
                self.assertNotIn("humanconfidence", self.cloud.json_calls[0])

    def test_a_challenge_redeems_once(self):
        self.build(level_answer("High"))
        page = self.page()["humanconfidencepage"]
        self.assertEqual(("High", "Active"),
                         self.read(self.process(page=page)))
        self.assert_low_and_active(self.process(page=page))

    def test_a_challenge_kept_too_long_gives_low_and_active(self):
        now = [1000.0]
        challenges = HumanConfidenceChallenges(
            lifetime_seconds=60, clock=lambda: now[0])
        self.build(level_answer("High"), challenges=challenges)
        page = self.page()["humanconfidencepage"]
        now[0] += 60
        self.assert_low_and_active(self.process(page=page))

    # Two reads of HumanConfidence for one request make one request to the
    # remote server.

    def test_two_reads_make_one_request(self):
        self.build(level_answer("Medium"))
        data = self.process()
        first = self.read(data)
        second = self.read(data)
        self.assertEqual(first, second)
        self.assertEqual(("Medium", "Active"), first)
        self.assertEqual(1, len(self.cloud.json_calls))

    # A request that carries a sealed value is neither stored in nor served
    # from a cache.

    def test_a_sealed_request_is_not_stored_in_a_cache(self):
        cache = BasicDictionaryCache()
        self.build(level_answer("High"), cache=cache)
        page = self.page()["humanconfidencepage"]
        self.process(page=page)
        self.process(page=page)
        self.assertEqual(2, len(self.cloud.json_calls))
        self.assertEqual({}, dict(cache.cache))

    def test_a_sealed_request_is_not_served_from_a_cache(self):
        class AlwaysHit(BasicDictionaryCache):
            entry = None

            def get_cache_value(self, key):
                return self.entry

        cache = AlwaysHit()
        self.build(level_answer("Medium"), cache=cache)
        cache.entry = AspectDataDictionary(self.engine, {"cloud": json.dumps(
            {"derived": {"humanconfidence": "High",
                         "humanconfidencesource": "Active"}})})
        data = self.process()
        self.assertEqual(("Medium", "Active"), self.read(data))
        self.assertEqual(1, len(self.cloud.json_calls))

    def test_a_request_without_a_sealed_value_still_uses_the_cache(self):
        cache = BasicDictionaryCache()
        self.build(Answer(json.dumps({"device": {"ismobile": True}})),
                   cache=cache)
        self.process(sealed=None, page="")
        self.process(sealed=None, page="")
        self.assertEqual(1, len(self.cloud.json_calls))

    # The call holds one challenge, being the one the package kept, where
    # the request's evidence also holds one.

    def test_the_call_holds_only_the_challenge_kept(self):
        self.build(level_answer("High"))
        page = self.page()
        self.process(page=page["humanconfidencepage"], evidence={
            "query.challenge": OTHER_CHALLENGE,
            "header.Challenge": OTHER_CHALLENGE,
            "cookie.CHALLENGE": OTHER_CHALLENGE,
            "server.challenge": OTHER_CHALLENGE})
        sent = self.cloud.json_calls[0]
        names = [name for name in sent if name.lower() == "challenge"]
        self.assertEqual(["challenge"], names)
        self.assertEqual(page["challenge"], sent["challenge"])
        self.assertNotIn(OTHER_CHALLENGE, json.dumps(sent))

    def test_a_challenge_in_the_request_alone_is_not_sent(self):
        self.build(level_answer("High"))
        self.process(page="", evidence={"query.challenge": OTHER_CHALLENGE})
        self.assertNotIn("challenge", self.cloud.json_calls[0])

    def test_the_sealed_value_sent_is_the_query_one_exactly(self):
        self.build(level_answer("High"))
        self.process(evidence={"header.HumanConfidence": "another"})
        sent = self.cloud.json_calls[0]
        self.assertEqual(
            ["humanconfidence"],
            [name for name in sent if name.lower() == "humanconfidence"])
        self.assertEqual(SEALED, sent["humanconfidence"])

    # No log entry and no error message holds the sealed value, the
    # License Key, or the challenge.

    def assert_holds_none(self, texts, values):
        for text in texts:
            for value in values:
                self.assertNotIn(value, text)

    def messages_of(self, data):
        texts = list(self.logger.messages)
        texts += [str(w.message) for w in self.process_warnings]
        for error in data.errors.values():
            texts.append(str(error.exception_instance))
            texts.append(error.exception_traceback)
            for inner in getattr(error.exception_instance,
                                 "exceptions", ()) or ():
                texts.append(str(inner))
        return texts

    def test_no_message_holds_the_sealed_value_key_or_challenge(self):
        page = {}

        def echo():
            # The answer names every value the call sent.
            return json.dumps({
                "errors": ["{} {} {}".format(
                    SEALED, LICENSE_KEY, page["challenge"])],
                "warnings": ["{} {} {}".format(
                    SEALED, LICENSE_KEY, page["challenge"])]})

        cases = {
            "errors and warnings": lambda: Answer(echo(), 400),
            "not JSON": lambda: Answer(
                "<p>{} {} {}</p>".format(
                    SEALED, LICENSE_KEY, page["challenge"]), 502),
            "connection": lambda: Answer(raises=requests.ConnectionError(
                "{} {} {}".format(SEALED, LICENSE_KEY, page["challenge"]))),
        }
        for case, answer in cases.items():
            with self.subTest(case=case):
                self.build(Answer())
                page.update(self.page())
                self.cloud.answer = answer()
                data = self.process(page=page["humanconfidencepage"])
                texts = self.messages_of(data)
                self.assertTrue(texts)
                self.assert_holds_none(
                    texts, (SEALED, LICENSE_KEY, page["challenge"]))
                self.assert_low_and_active(data)

    def test_no_conflict_warning_holds_the_sealed_value(self):
        self.build(level_answer("High"))
        self.process(evidence={
            "cookie.humanconfidencex": SEALED,
            "header.humanconfidencex": SEALED})
        texts = [str(w.message) for w in self.process_warnings]
        self.assertTrue(texts)
        self.assert_holds_none(texts, (SEALED,))

    # The consumer never handles the challenge.

    def test_the_sealed_value_is_not_in_any_element_data(self):
        self.build(level_answer("High"))
        page = self.page()
        data = self.process(page=page["humanconfidencepage"])
        for key in ("cloud-response", "derived"):
            text = json.dumps(data.get(key).as_dictionary(), default=str)
            for value in (SEALED, page["challenge"], LICENSE_KEY):
                self.assertNotIn(value, text)


class TestHumanConfidenceChallenges(CloudRequestEngineTestsBase):

    def test_each_page_gets_a_new_challenge(self):
        challenges = HumanConfidenceChallenges()
        issued = [challenges.issue() for _ in range(100)]
        self.assertEqual(100, len({page for page, _ in issued}))
        self.assertEqual(100, len({challenge for _, challenge in issued}))

    def test_a_challenge_is_taken_once(self):
        challenges = HumanConfidenceChallenges()
        page, challenge = challenges.issue()
        self.assertEqual(challenge, challenges.take(page))
        self.assertIsNone(challenges.take(page))

    def test_the_oldest_challenge_goes_when_full(self):
        challenges = HumanConfidenceChallenges(capacity=2)
        first, _ = challenges.issue()
        second, kept = challenges.issue()
        challenges.issue()
        self.assertIsNone(challenges.take(first))
        self.assertEqual(kept, challenges.take(second))

    def test_a_page_value_that_is_not_text_has_no_challenge(self):
        challenges = HumanConfidenceChallenges()
        challenges.issue()
        for page in (None, "", 5):
            self.assertIsNone(challenges.take(page))

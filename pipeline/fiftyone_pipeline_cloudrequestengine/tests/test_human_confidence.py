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
A sealed Human Confidence result is redeemed by the package, through the
Cloud Request Engine's one JSON call, with the transaction the package kept
for the page. These are the required tests of the Human Confidence page of
the pipeline specification, against a stand-in for the cloud service.
"""

import json
import unittest
import urllib.parse
import warnings
from unittest.mock import Mock

import requests

from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_cloudrequestengine.humanconfidence import \
    DerivedCloud, HumanConfidenceTransactions
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.basic_dictionary_cache import \
    BasicDictionaryCache

RESOURCE = "resource_key"
LICENCE = "LICENCEKEY1234567890"
SEALED = "sealed-result-0123456789"
API = "https://cloud.example/api/v4/"


def reply(body, status=200):
    text = body if isinstance(body, str) else json.dumps(body)
    response = Mock(spec=requests.Response)
    response.status_code = status
    response.text = text
    response.json = lambda: json.loads(text)
    response.headers = {}
    response.url = API
    return response


class StandIn(object):
    """Answers discovery for a key carrying the two properties, and each
    data request with the answer set, keeping the data requests made."""

    def __init__(self):
        self.answer = reply({"derived": {
            "humanconfidence": "High", "humanconfidencesource": "Active"}})
        self.data_requests = []

    def request(self, type, url, content, origin):
        if "accessibleProperties" in url:
            return reply({"Products": {"derived": {"Properties": [
                {"Name": "HumanConfidence", "Type": "String"},
                {"Name": "HumanConfidenceSource", "Type": "String"}]}}})
        if url.endswith("evidencekeys"):
            return reply(["header.user-agent", "query.humanconfidence"])
        self.data_requests.append(dict(content or {}))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


class HumanConfidenceTests(unittest.TestCase):

    def setUp(self):
        self.cloud = StandIn()
        self.transactions = HumanConfidenceTransactions()

    def pipeline(self, license_key=LICENCE, cache=None, requested=None):
        settings = {
            "resource_key": RESOURCE, "http_client": self.cloud,
            "cloud_endpoint": API,
            "human_confidence_transactions": self.transactions}
        if license_key:
            settings["license_key"] = license_key
        if requested:
            settings["requested_properties"] = requested
        engine = CloudRequestEngine(settings)
        if cache is not None:
            engine.set_cache(cache)
        pipeline = PipelineBuilder({
            "add_javascript_builder": False,
            "use_setheader_properties": False,
            "suppress_process_exceptions": True}) \
            .add(engine).add(DerivedCloud()).build()
        self.addCleanup(pipeline.close)
        return pipeline

    def process(self, pipeline, page=True, sealed=SEALED, **evidence):
        data = pipeline.create_flowdata()
        data.evidence.add("header.user-agent", "Mozilla/5.0")
        if sealed is not None:
            data.evidence.add("query.humanconfidence", sealed)
        if page is True:
            page = self.transactions.issue()
            self.page = page
        if page:
            data.evidence.add("query.humanconfidencepage", page.id)
        for key, value in evidence.items():
            data.evidence.add(key.replace("_", "."), value)
        data.process()
        return data

    def kept_transaction(self):
        query = urllib.parse.urlparse(self.page.script_url(API, RESOURCE))
        return urllib.parse.parse_qs(query.query)["transaction"][0]

    def assert_values(self, data, value, source="Active"):
        self.assertEqual(value, data.derived.humanconfidence.value())
        self.assertEqual(source, data.derived.humanconfidencesource.value())

    def assert_no_derived_error(self, data):
        self.assertNotIn("derived", data.errors)

    # A sealed result that redeems.

    def test_a_redeemed_value_is_human_confidence_with_source_active(self):
        for value in ("High", "Medium", "Low"):
            with self.subTest(value=value):
                self.cloud.answer = reply({"derived": {
                    "humanconfidence": value,
                    "humanconfidencesource": "Passive"}})
                data = self.process(self.pipeline())
                self.assert_values(data, value)
                self.assertEqual({}, dict(data.errors))

    def test_the_call_holds_the_sealed_result_and_the_kept_transaction(self):
        self.process(self.pipeline())
        sent = self.cloud.data_requests[-1]
        self.assertEqual(SEALED, sent["humanconfidence"])
        self.assertEqual(self.kept_transaction(), sent["transaction"])
        self.assertEqual(LICENCE, sent["license"])
        self.assertIn("derived.humanconfidence", sent["values"].split(","))
        # The page handle is the package's own and goes nowhere.
        self.assertNotIn("humanconfidencepage", sent)

    def test_the_call_holds_only_the_kept_transaction(self):
        self.process(self.pipeline(), query_transaction="from-the-page",
                     header_transaction="from-a-header",
                     cookie_Challenge="from-a-cookie",
                     query_challenge="from-the-page")
        sent = self.cloud.data_requests[-1]
        self.assertEqual(self.kept_transaction(), sent["transaction"])
        self.assertEqual(
            ["transaction"],
            [name for name in sent
             if name.lower() in ("transaction", "challenge")])

    def test_an_added_property_is_left_out_of_the_report(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.cloud.answer = reply({
                "device": {"ismobile": False},
                "derived": {"humanconfidence": "High"}})
            self.process(self.pipeline(requested=["device.ismobile"]))
        self.assertEqual([], [str(w.message) for w in caught
                              if "humanconfidence" in str(w.message)])
        sent = self.cloud.data_requests[-1]
        self.assertEqual("device.ismobile,derived.humanconfidence",
                         sent["values"])

    # Each case where the sealed result is not redeemed.

    def assert_not_redeemed(self, data):
        self.assert_values(data, "Medium")
        self.assert_no_derived_error(data)

    def test_no_licence_key_gives_medium_and_sends_no_sealed_result(self):
        data = self.process(self.pipeline(license_key=None))
        self.assert_not_redeemed(data)
        sent = self.cloud.data_requests[-1]
        self.assertNotIn("humanconfidence", sent)
        self.assertNotIn("transaction", sent)

    def test_no_kept_transaction_gives_medium(self):
        pipeline = self.pipeline()
        for page in (None, Mock(id="never-issued")):
            with self.subTest(page=page):
                data = self.process(pipeline, page=page)
                self.assert_not_redeemed(data)
                self.assertNotIn("humanconfidence",
                                 self.cloud.data_requests[-1])

    def test_a_transaction_used_before_gives_medium(self):
        pipeline = self.pipeline()
        self.process(pipeline)
        data = self.process(pipeline, page=self.page)
        self.assert_not_redeemed(data)
        self.assertNotIn("humanconfidence", self.cloud.data_requests[-1])

    def test_a_failed_request_gives_medium_and_one_error(self):
        for failure in (requests.exceptions.ConnectionError("refused"),
                        requests.exceptions.Timeout("timed out"),
                        reply("Bad Gateway", 502)):
            with self.subTest(failure=failure):
                self.cloud.answer = failure
                data = self.process(self.pipeline())
                self.assert_not_redeemed(data)
                self.assertEqual(["cloud"], list(data.errors))

    def test_an_errors_list_gives_medium(self):
        self.cloud.answer = reply({"errors": [
            "HumanConfidence is not covered by the license key."]}, 400)
        data = self.process(self.pipeline())
        self.assert_not_redeemed(data)
        self.assertEqual(["cloud"], list(data.errors))

    def test_no_value_in_the_response_gives_medium(self):
        for body in ({"device": {"ismobile": True}},
                     {"derived": {"humanconfidencesource": "Active"}},
                     {"derived": {"humanconfidence": None,
                                  "humanconfidencenullreason": "Not here."}},
                     {"derived": {"humanconfidence": "Unknown"}},
                     {"derived": {"humanconfidence": "high"}},
                     {"derived": {"humanconfidence": 3}},
                     {"derived": "High"}):
            with self.subTest(body=body):
                self.cloud.answer = reply(body)
                data = self.process(self.pipeline())
                self.assert_not_redeemed(data)
                self.assertEqual({}, dict(data.errors))

    # Reads, the cache and messages.

    def test_two_reads_make_one_request(self):
        data = self.process(self.pipeline())
        first = data.derived.humanconfidence.value()
        second = data.derived.get("HumanConfidence").value()
        self.assertEqual(first, second)
        self.assertEqual(1, len(self.cloud.data_requests))

    def test_a_request_with_a_sealed_result_skips_the_cache(self):
        cache = BasicDictionaryCache()
        pipeline = self.pipeline(cache=cache)
        # The same evidence without a sealed result is stored.
        self.process(pipeline, sealed=None, page=None)
        self.process(pipeline, sealed=None, page=None)
        self.assertEqual(1, len(self.cloud.data_requests))
        stored = dict(cache.cache)
        self.process(pipeline)
        self.process(pipeline)
        self.assertEqual(3, len(self.cloud.data_requests))
        self.assertEqual(stored, dict(cache.cache))

    def test_no_message_holds_the_sealed_result_licence_or_transaction(self):
        secrets = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            pipeline = self.pipeline()
            page = self.transactions.issue()
            self.page = page
            transaction = self.kept_transaction()
            secrets = [SEALED, LICENCE, transaction, LICENCE[-4:]]
            self.cloud.answer = reply({
                "errors": ["Not valid: " + SEALED + " " + transaction
                           + " " + LICENCE],
                "warnings": ["Echo " + SEALED + " " + LICENCE]}, 400)
            data = self.process(
                pipeline, page=page, header_humanconfidence=SEALED,
                cookie_humanconfidence=SEALED)
        messages = [str(w.message) for w in caught]
        messages += [str(error.exception_instance)
                     for error in data.errors.values()]
        messages += [repr(page)]
        self.assertTrue(data.errors)
        for message in messages:
            for secret in secrets:
                self.assertNotIn(secret, message)

    # A sealed result anywhere but a non-empty query.humanconfidence.

    def test_a_sealed_result_under_another_key_is_not_sent(self):
        cases = (
            {"header_humanconfidence": SEALED},
            {"cookie_HumanConfidence": SEALED},
            {"humanconfidence": SEALED},
            {"server_humanconfidence": SEALED})
        for sealed in (None, ""):
            for evidence in cases:
                with self.subTest(query=sealed, evidence=evidence):
                    data = self.process(
                        self.pipeline(), sealed=sealed,
                        query_transaction="from-the-page",
                        header_transaction="from-a-header",
                        cookie_challenge="from-a-cookie",
                        **evidence)
                    sent = self.cloud.data_requests[-1]
                    self.assertEqual(
                        [], [name for name in sent if name.lower() in (
                            "humanconfidence", "transaction", "challenge")])
                    self.assertEqual({}, dict(data.errors))

    def test_an_empty_human_confidence_changes_nothing(self):
        self.process(self.pipeline(), sealed="", page=None,
                     header_humanconfidence="",
                     query_transaction="from-the-page")
        sent = self.cloud.data_requests[-1]
        self.assertEqual("from-the-page", sent["transaction"])

    def test_without_a_sealed_result_the_response_is_read_as_before(self):
        self.cloud.answer = reply({"derived": {
            "humanconfidence": "Low", "humanconfidencesource": "Passive"}})
        data = self.process(self.pipeline(), sealed=None, page=None)
        self.assert_values(data, "Low", "Passive")
        self.assertNotIn("transaction", self.cloud.data_requests[-1])

    def test_a_credential_without_the_property_gives_its_reason(self):
        reason = "The resource key does not include this property."
        self.cloud.answer = reply({"derived": {
            "humanconfidence": None, "humanconfidencenullreason": reason,
            "humanconfidencesource": None,
            "humanconfidencesourcenullreason": reason}})
        data = self.process(self.pipeline(), sealed=None, page=None)
        for name in ("humanconfidence", "humanconfidencesource"):
            value = data.derived.get(name)
            self.assertFalse(value.has_value())
            self.assertEqual(reason, value.no_value_message())

    # The transactions.

    def test_each_page_gets_a_new_transaction_used_once(self):
        first, second = self.transactions.issue(), self.transactions.issue()
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.script_url(API, RESOURCE),
                            second.script_url(API, RESOURCE))
        self.assertIsNotNone(self.transactions._take(first.id))
        self.assertIsNone(self.transactions._take(first.id))
        self.assertTrue(first.script_url(API, RESOURCE).startswith(
            API + RESOURCE + ".js?transaction="))

    def test_the_consumer_has_no_accessor_for_a_transaction(self):
        engine = self.pipeline().get_element("cloud")
        for store in (self.transactions, engine.human_confidence_transactions,
                      HumanConfidenceTransactions()):
            with self.subTest(store=store):
                public = [name for name in dir(store)
                          if not name.startswith("_")
                          and callable(getattr(store, name))]
                self.assertEqual(["issue"], public)

    def test_an_old_or_pushed_out_transaction_is_dropped(self):
        transactions = HumanConfidenceTransactions(lifetime_seconds=0)
        self.assertIsNone(transactions._take(transactions.issue().id))
        transactions = HumanConfidenceTransactions(capacity=1)
        first = transactions.issue()
        transactions.issue()
        self.assertIsNone(transactions._take(first.id))


if __name__ == "__main__":
    unittest.main()

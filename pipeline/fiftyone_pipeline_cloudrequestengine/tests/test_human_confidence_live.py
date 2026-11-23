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
Human Confidence against the cloud service that _51DEGREES_CLOUD_ENDPOINT
names, or the public cloud where it is not set. The tests need a Resource
Key that carries HumanConfidence, and a License Key of the same account,
and skip where either is not set.

A sealed value is made only by the browser tests in a page, so these tests
send one that does not redeem and check it gives Low and Active, through
the same JSON call a sealed value that redeems goes through.
"""

import unittest
import warnings

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import \
    CloudRequestEngine
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from .live_cloud import find_resource_key, no_resource_key, read_environment

RESOURCE_KEY = find_resource_key()
LICENSE_KEY_NAME = "_51DEGREES_LICENSE_KEY_BESPOKE"
LICENSE_KEY = read_environment(LICENSE_KEY_NAME) or ""

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LEVELS = ("High", "Medium", "Low")
SOURCES = ("Active", "Passive")


@unittest.skipUnless(RESOURCE_KEY, no_resource_key(
    "the derived product", "HumanConfidence", several=True))
@unittest.skipUnless(
    LICENSE_KEY != "",
    f"{LICENSE_KEY_NAME} is not set. Set it to a License Key of the account "
    "that holds the Resource Key to run the live Human Confidence tests.")
class HumanConfidenceLiveTests(unittest.TestCase):

    def setUp(self):
        self.engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "license_key": LICENSE_KEY,
            "timeout_seconds": 10})
        derived = CloudEngine()
        derived.datakey = "derived"
        self.pipeline = PipelineBuilder({
            "suppress_process_exceptions": True}).add(
                self.engine).add(derived).build()
        self.addCleanup(self.pipeline.close)

    def process(self, evidence):
        data = self.pipeline.create_flowdata()
        data.evidence.add("header.user-agent", USER_AGENT)
        for key, value in evidence.items():
            data.evidence.add(key, value)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            data.process()
        derived = data.get("derived")
        return (data,
                derived.get("humanconfidence").value(),
                derived.get("humanconfidencesource").value())

    def test_a_request_without_a_sealed_value_gives_a_passive_level(self):
        data, level, source = self.process({})
        self.assertEqual({}, data.errors)
        self.assertIn(level, LEVELS)
        self.assertEqual("Passive", source)

    def test_a_sealed_value_that_does_not_redeem_gives_low_and_active(self):
        page = self.engine.human_confidence_page_values()
        data, level, source = self.process({
            "query.humanconfidence": "a-value-the-cloud-did-not-seal",
            "query.humanconfidencepage": page["humanconfidencepage"]})
        self.assertIn(level, LEVELS)
        self.assertIn(source, SOURCES)
        self.assertEqual(("Low", "Active"), (level, source))
        for error in data.errors.values():
            text = str(error.exception_instance)
            self.assertNotIn(LICENSE_KEY, text)
            self.assertNotIn(page["challenge"], text)

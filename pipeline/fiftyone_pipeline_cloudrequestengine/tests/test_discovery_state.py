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
A Cloud Request Engine can be built from a saved copy of what an earlier
engine discovered, being the accepted Evidence keys and the accessible
Properties, and then makes no discovery request, as cloud-request-engine.md
lines 307 to 314 ask. The copy is read back from an engine whose discovery
has completed, as one JSON document of the form the Java package writes.
"""

import json
import unittest

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine

from .classes.cloudrequestengine_testbase import CloudRequestEngineTestsBase
from .classes.constants import Constants
from .test_discovery_at_build import (
    DATA, EVIDENCE_KEYS, PROPERTIES, UNAVAILABLE, DiscoveryClient, answering,
    build, build_quietly, pipeline_for, process)


def device_engine():
    engine = CloudEngine()
    engine.datakey = "device"
    return engine


class DiscoveryStateTests(CloudRequestEngineTestsBase):

    def saved_copy(self):
        return build(DiscoveryClient()).discovery_state()

    def test_the_copy_is_one_json_document(self):
        document = json.loads(self.saved_copy())

        self.assertEqual(
            {"evidenceKeys", "accessibleProperties"}, set(document))
        self.assertEqual(
            json.loads(Constants.evidenceKeysResponse),
            document["evidenceKeys"])
        self.assertEqual(
            Constants.accessiblePropertiesResponse,
            document["accessibleProperties"])

    def test_an_engine_built_from_the_copy_makes_no_discovery_request(self):
        first = build(DiscoveryClient())
        client = DiscoveryClient()

        engine = build(client, discovery_state=first.discovery_state())

        self.assertEqual(0, client.count(PROPERTIES))
        self.assertEqual(0, client.count(EVIDENCE_KEYS))
        self.assertEqual(
            first.flow_element_properties, engine.flow_element_properties)
        self.assertEqual(first.evidence_keys, engine.evidence_keys)
        self.assertEqual(first.discovery_state(), engine.discovery_state())

    def test_an_engine_built_from_the_copy_processes(self):
        client = DiscoveryClient()
        engine = build(client, discovery_state=self.saved_copy())
        device = device_engine()
        pipeline = pipeline_for(engine, device)

        data = process(pipeline)

        self.assertEqual({}, data.errors)
        self.assertEqual(["value"], list(device.get_properties()))
        self.assertEqual(0, client.count(PROPERTIES))
        self.assertEqual(0, client.count(EVIDENCE_KEYS))
        self.assertEqual(1, client.count(DATA))

    def test_the_copy_may_be_given_as_a_dictionary(self):
        client = DiscoveryClient()

        engine = build(
            client, discovery_state=json.loads(self.saved_copy()))

        self.assertEqual(0, client.count(PROPERTIES))
        self.assertEqual(
            json.loads(Constants.evidenceKeysResponse), engine.evidence_keys)

    def test_there_is_no_copy_while_discovery_has_not_completed(self):
        client = DiscoveryClient()
        client.failures[PROPERTIES] = answering(503, UNAVAILABLE)

        engine = build_quietly(client)

        self.assertIsNone(engine.discovery_state())

    def test_a_copy_that_is_not_one_is_refused_with_no_request(self):
        for state in ("{}", '{"evidenceKeys": "a", "accessibleProperties": {}}',
                      "not json", 7):
            with self.subTest(state=state):
                client = DiscoveryClient()
                with self.assertRaises(ValueError) as raised:
                    build(client, discovery_state=state)
                self.assertIn("discovery_state", str(raised.exception))
                self.assertEqual([], client.requests)


if __name__ == "__main__":
    unittest.main()

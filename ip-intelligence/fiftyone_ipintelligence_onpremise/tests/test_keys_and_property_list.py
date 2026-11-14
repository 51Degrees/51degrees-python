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

import os
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import \
    IpIntelligenceOnPremisePipelineBuilder

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


def build(**settings):
    return IpIntelligenceOnPremisePipelineBuilder(
        data_file_path=data_file, licence_keys="", usage_sharing=False,
        **settings).build()


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the _51DEGREES_IPI_PATH environment variable." % data_file)
class PropertyListTests(unittest.TestCase):
    """!
    A configuration file gives a list of strings as one comma-separated
    string, so restricted_properties takes that form as well as a list.
    """

    def setUp(self):
        # Two names the data file holds, as the native code gives them.
        pipeline = build()
        self.addCleanup(pipeline.close)
        engine = pipeline.get_element("ip").engine
        self.names = list(engine.getRequiredProperties())[:2]
        self.assertEqual(2, len(self.names))

    def check(self, pipeline):
        self.addCleanup(pipeline.close)
        self.assertEqual(
            self.names, pipeline.get_element("ip").build_property_names)

    def test_a_comma_separated_string_names_each_property(self):
        self.check(build(restricted_properties=" , ".join(self.names)))

    def test_a_configuration_file_names_each_property(self):
        self.check(PipelineBuilder().build_from_configuration({
            "PipelineOptions": {
                "Elements": [{
                    "elementName": "IpIntelligenceOnPremise",
                    "elementPath": "fiftyone_ipintelligence_onpremise."
                                   "ipintelligence_onpremise",
                    "elementParameters": {
                        "data_file_path": data_file,
                        "licence_keys": "",
                        "restricted_properties": ",".join(self.names)
                    }
                }]
            }
        }))

    def test_the_callers_list_is_left_as_it_was(self):
        names = list(self.names)
        self.check(build(restricted_properties=names))
        self.assertEqual(self.names, names)


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the _51DEGREES_IPI_PATH environment variable." % data_file)
class EvidenceKeysTests(unittest.TestCase):
    """!
    The Evidence keys come from the data file, so the engine reads them
    at start-up and again whenever the data is refreshed.
    """

    def test_the_keys_are_read_again_when_the_data_is_refreshed(self):
        pipeline = build(file_system_watcher=True)
        self.addCleanup(pipeline.close)
        engine = pipeline.get_element("ip")
        keys = list(engine.evidence_keys_list)
        client_ip_keys = list(engine.client_ip_keys)
        self.assertNotEqual([], client_ip_keys)

        # Stands for the keys of the data loaded before the refresh.
        engine.evidence_keys_list = ["query.x-from-the-earlier-data"]
        engine.client_ip_keys = []
        engine.data_file.refresh()

        self.assertEqual(keys, engine.evidence_keys_list)
        self.assertEqual(client_ip_keys, engine.client_ip_keys)

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
from fiftyone_devicedetection_onpremise.DeviceDetectionHashEngineModule import ConfigHashSwig
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import DeviceDetectionOnPremise
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder

# The free Lite data file, where cxx/data/get-data-files.ps1 and
# get-data-files.sh download it and where CI links it in.
DATA_FILE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cxx",
    "data", "device-detection", "51Degrees-LiteV4.1.hash"))

# The collections whose settings the configuration exposes.
COLLECTIONS = (
    "Strings", "Properties", "Values", "Profiles", "Nodes", "ProfileOffsets")

# Each profile name the engine accepts and the native setter it maps to.
PROFILES = {
    "LowMemory": "setLowMemory",
    "MaxPerformance": "setMaxPerformance",
    "Balanced": "setBalanced",
    "BalancedTemp": "setBalancedTemp",
    "HighPerformance": "setHighPerformance",
}


def collection_settings(config):
    """
    Whether each collection is loaded into memory and how many items it
    caches, which are what a performance profile sets.
    """
    settings = {}
    for name in COLLECTIONS:
        collection = getattr(config, "get" + name)()
        settings[name] = (collection.getLoaded(), collection.getCapacity())
    return settings


def profile_settings(setter):
    """The collection settings the native code gives a profile."""
    config = ConfigHashSwig()
    getattr(config, setter)()
    return collection_settings(config)


@unittest.skipUnless(
    os.path.isfile(DATA_FILE),
    "The free Lite data file is not at {0}. Download it with "
    "cxx/data/get-data-files.ps1 or cxx/data/get-data-files.sh, after "
    "'git submodule update --init --recursive'.".format(DATA_FILE))
class PerformanceProfileDefaultTests(unittest.TestCase):
    """
    The engine keeps no name for the profile in use, so these tests compare
    the collection settings of the configuration the engine gives the
    native code with the settings each profile has there. MaxPerformance
    and LowMemory have the same collection settings, and Balanced and
    BalancedTemp do too, so neither pair can be told apart this way.
    """

    def _engine_settings(self, **settings):
        engine = DeviceDetectionOnPremise(
            data_file_path=DATA_FILE, licence_keys="", **settings)
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        self.assertIsNotNone(engine.engine)
        return collection_settings(engine.config)

    def test_balanced_and_low_memory_differ(self):
        self.assertNotEqual(
            profile_settings("setBalanced"), profile_settings("setLowMemory"))

    def test_engine_defaults_use_balanced(self):
        self.assertEqual(
            profile_settings("setBalanced"), self._engine_settings())

    def test_builder_defaults_use_balanced(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=DATA_FILE, usage_sharing=False,
            licence_keys="").build()
        self.addCleanup(pipeline.close)
        engine = pipeline.get_element("device")
        self.assertEqual(
            profile_settings("setBalanced"),
            collection_settings(engine.config))

    def test_each_named_profile_is_used(self):
        for name, setter in PROFILES.items():
            with self.subTest(name):
                self.assertEqual(
                    profile_settings(setter),
                    self._engine_settings(performance_profile=name))

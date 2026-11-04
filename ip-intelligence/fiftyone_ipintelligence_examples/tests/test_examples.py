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

from fiftyone_pipeline_core.logger import Logger

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_FILE_NAME

# The tests run against the freely available ASN data file the data
# repository links to, so they only rely on properties that the free data
# file provides (location properties such as Latitude, Longitude and Areas
# are not present in it).
data_file = ExampleUtils.find_file(ASN_DATAFILE_NAME)
evidence_file = ExampleUtils.find_file(EVIDENCE_FILE_NAME)
truth_file = ExampleUtils.find_file("geoip_comparison_evidence.csv")
resource_key = ExampleUtils.get_resource_key()

# The mixed examples combine IP intelligence with device detection, which is
# an optional dependency. Their tests only run when it is installed.
try:
    import fiftyone_devicedetection_onpremise  # noqa: F401
    import fiftyone_devicedetection_cloud  # noqa: F401
    device_detection_available = True
except ImportError:
    device_detection_available = False

# Look for any of the known device detection data file names, in the same
# priority order as the .NET mixed example.
hash_file = None
for _hash_name in ["51Degrees-LiteV4.1.hash", "TAC-HashV41.hash"]:
    hash_file = ExampleUtils.find_file(_hash_name)
    if hash_file:
        break


class ExampleTests(unittest.TestCase):

    @unittest.skipUnless(
        bool(data_file), "No IP intelligence data file available")
    def test_onpremise_datafile_loads(self):
        # Verify the freely available ASN data file loads and processes
        # correctly.
        from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
        pipeline = IpIntelligencePipelineBuilder(
            data_file_path=data_file,
            performance_profile="LowMemory",
            usage_sharing=False,
            auto_update=False,
            licence_keys="").build()
        self.addCleanup(pipeline.close)
        data = pipeline.create_flowdata()
        self.addCleanup(data.close)
        data.evidence.add_from_dict({"query.client-ip": "8.8.8.8"})
        data.process()
        # The supplied IP address is echoed back in the results.
        self.assertTrue(data.ip.ip.has_value())
        self.assertEqual(data.ip.ip.value(), "8.8.8.8")

    @unittest.skipUnless(
        bool(data_file), "No IP intelligence data file available")
    def test_onpremise_gettingstarted_console(self):
        from fiftyone_ipintelligence_examples.onpremise.gettingstarted_console import GettingStartedConsole
        example = GettingStartedConsole()
        example.run(data_file, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        bool(data_file), "No IP intelligence data file available")
    def test_onpremise_countries_console(self):
        from fiftyone_ipintelligence_examples.onpremise.countries_console import CountriesConsole
        example = CountriesConsole()
        example.run(data_file, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        bool(data_file), "No IP intelligence data file available")
    def test_onpremise_metadata_console(self):
        from fiftyone_ipintelligence_examples.onpremise.metadata_console import MetadataConsole
        example = MetadataConsole()
        example.run(data_file, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        bool(data_file) and bool(evidence_file),
        "No IP intelligence data file or evidence file available")
    def test_onpremise_offlineprocessing(self):
        from fiftyone_ipintelligence_examples.onpremise import offlineprocessing
        example = offlineprocessing.OfflineProcessing()
        output = []
        example.run(
            data_file,
            evidence_file,
            Logger(min_level="error"),
            output.append)
        # document separators + records + end marker
        self.assertGreater(len(output), offlineprocessing.RECORD_LIMIT)

    @unittest.skipUnless(
        bool(data_file) and bool(evidence_file),
        "No IP intelligence data file or evidence file available")
    def test_onpremise_performance_console(self):
        from fiftyone_ipintelligence_examples.onpremise import performance_console
        evidence = performance_console.load_evidence(evidence_file, 50)
        results = performance_console.PerformanceConsole().run(
            data_file,
            evidence,
            Logger(min_level="error"),
            lambda x: None,
            workers=1,
            performance_profile="LowMemory")
        self.assertGreater(results["DetectionsPerSecond"], 0)

    @unittest.skipUnless(
        bool(data_file) and bool(truth_file),
        "No data file or truth file available")
    def test_onpremise_compare_console(self):
        from fiftyone_ipintelligence_examples.onpremise.compare_console import CompareConsole
        import io
        output = io.StringIO()
        CompareConsole().run(
            data_file,
            truth_file,
            Logger(min_level="error"),
            output,
            record_limit=20)
        # header + up to 20 records
        self.assertGreater(len(output.getvalue().splitlines()), 1)

    @unittest.skipUnless(
        bool(resource_key), "No resource_key environment variable set")
    def test_cloud_gettingstarted_console(self):
        from fiftyone_ipintelligence_examples.cloud.gettingstarted_console import GettingStartedConsole
        example = GettingStartedConsole()
        example.run(resource_key, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        bool(resource_key), "No resource_key environment variable set")
    def test_cloud_metadata_console(self):
        from fiftyone_ipintelligence_examples.cloud.metadata_console import MetadataConsole
        example = MetadataConsole()
        example.run(resource_key, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        bool(resource_key), "No resource_key environment variable set")
    def test_cloud_getallproperties_console(self):
        from fiftyone_ipintelligence_examples.cloud.getallproperties_console import GetAllPropertiesConsole
        example = GetAllPropertiesConsole()
        example.run(resource_key, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        device_detection_available and bool(hash_file) and bool(data_file),
        "device detection package or data file not available")
    def test_onpremise_mixed_console(self):
        from fiftyone_ipintelligence_examples.onpremise.mixed_console import MixedConsole
        example = MixedConsole()
        example.run(hash_file, data_file, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        device_detection_available and bool(resource_key),
        "device detection package or resource_key not available")
    def test_cloud_mixed_console(self):
        from fiftyone_ipintelligence_examples.cloud.mixed_console import MixedConsole
        example = MixedConsole()
        example.run(resource_key, Logger(min_level="error"), lambda x: None)


if __name__ == "__main__":
    unittest.main()

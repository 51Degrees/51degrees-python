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
from unittest import mock

from fiftyone_pipeline_core.logger import Logger

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.constants import Constants
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME
from fiftyone_ipintelligence_shared.example_constants import EVIDENCE_FILE_NAME

from . import known_address
from .live_cloud import find_resource_key, no_resource_key

# The tests run against the freely available ASN data file the data
# repository links to, so they only rely on properties that the free data
# file provides (location properties such as Latitude, Longitude and Areas
# are not present in it).
data_file = ExampleUtils.find_file(ASN_DATAFILE_NAME)
evidence_file = ExampleUtils.find_file(EVIDENCE_FILE_NAME)
truth_file = ExampleUtils.find_file("geoip_comparison_evidence.csv")
resource_key = find_resource_key()

NO_IP_KEY = no_resource_key(
    "the ip product",
    "IP Intelligence properties such as RegisteredName, and their metadata")
NO_MIXED_KEY = no_resource_key(
    "the device and ip products",
    "device detection and IP Intelligence properties together")
NO_COUNTRIES_KEY = no_resource_key(
    "the ip and countrynamestranslated products",
    "the countries an IP address is most likely in, with their names "
    "translated")

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

# The evidence that has an example look up the known address.
KNOWN_EVIDENCE = {
    Constants.EVIDENCE_QUERY_CLIENT_IP_KEY: known_address.ADDRESS}


def require_known_results(test, printed, with_range):
    """Fail the test unless the example printed the registered name and the
    country of the known address, and, when with_range is true, the range
    that holds it."""
    output = "\n".join(printed)
    results = known_address.results_for(printed, known_address.ADDRESS)
    test.assertIsNotNone(
        results,
        f"The example printed no results for {known_address.ADDRESS}.\n"
        f"{output}")
    test.assertIn(
        known_address.REGISTERED_NAME, results,
        f"The results for {known_address.ADDRESS} should give "
        f"{known_address.REGISTERED_NAME} as the registered name.\n{output}")
    test.assertTrue(
        any(country in results for country in known_address.COUNTRY),
        f"The results for {known_address.ADDRESS} should give "
        f"{' or '.join(known_address.COUNTRY)} as the country.\n{output}")
    if with_range:
        test.assertTrue(
            any(end in results for end in known_address.RANGE),
            f"The results for {known_address.ADDRESS} should give the "
            f"range from {known_address.RANGE[0]} to "
            f"{known_address.RANGE[1]}.\n{output}")


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
    def test_onpremise_datafileupdate_programmatic(self):
        # The update the example asks for itself, which needs no licence
        # key, as the application already holds the new data.
        from fiftyone_ipintelligence_examples.onpremise.datafileupdate_console import DataFileUpdateConsole
        printed = []
        DataFileUpdateConsole().update_programmatically(
            data_file, printed.append)
        shown = "\n".join(printed)
        self.assertIn("A programmatic update needs no licence key", shown)
        self.assertIn(
            "gave the status UpdateStatus.AUTO_UPDATE_SUCCESS", shown)
        self.assertIn("file published on", shown)

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

    def test_cloud_gettingstarted_console(self):
        if not resource_key:
            self.skipTest(NO_IP_KEY)
        from fiftyone_ipintelligence_examples.cloud import gettingstarted_console
        printed = []
        # The example looks up the known address after its own ones.
        with mock.patch.object(
                gettingstarted_console, "EVIDENCE_VALUES",
                gettingstarted_console.EVIDENCE_VALUES + [KNOWN_EVIDENCE]):
            gettingstarted_console.GettingStartedConsole().run(
                resource_key, Logger(min_level="error"), printed.append)
        require_known_results(self, printed, with_range=True)

    def test_cloud_metadata_console(self):
        if not resource_key:
            self.skipTest(NO_IP_KEY)
        from fiftyone_ipintelligence_examples.cloud.metadata_console import MetadataConsole
        printed = []
        MetadataConsole().run(
            resource_key, Logger(min_level="error"), printed.append)
        output = "\n".join(printed)
        self.assertIn("\tProperty - ", output,
                      "The example should list the properties.\n" + output)
        self.assertIn("Accepted evidence keys:", output,
                      "The example should list the accepted evidence "
                      "keys.\n" + output)

    def test_cloud_getallproperties_console(self):
        if not resource_key:
            self.skipTest(NO_IP_KEY)
        from fiftyone_ipintelligence_examples.cloud import getallproperties_console
        printed = []
        with mock.patch.object(
                getallproperties_console, "SOME_IP_ADDRESS",
                known_address.ADDRESS):
            getallproperties_console.GetAllPropertiesConsole().run(
                resource_key, Logger(min_level="error"), printed.append)
        output = "\n".join(printed)
        self.assertIn(
            "What property values are associated with the IP "
            f"'{known_address.ADDRESS}'?", output)
        self.assertRegex(
            output,
            rf"(?im)^\tregisteredname = .*{known_address.REGISTERED_NAME}",
            f"The example should give {known_address.REGISTERED_NAME} as "
            f"the registered name of {known_address.ADDRESS}.")

    @unittest.skipUnless(
        device_detection_available and bool(hash_file) and bool(data_file),
        "device detection package or data file not available")
    def test_onpremise_mixed_console(self):
        from fiftyone_ipintelligence_examples.onpremise.mixed_console import MixedConsole
        example = MixedConsole()
        example.run(hash_file, data_file, Logger(min_level="error"), lambda x: None)

    @unittest.skipUnless(
        device_detection_available, "device detection package not available")
    def test_cloud_mixed_console(self):
        if not resource_key:
            self.skipTest(NO_MIXED_KEY)
        from fiftyone_ipintelligence_examples.cloud import mixed_console
        # The known address, with the User-Agent of the example's first
        # evidence. The example shows no range, so none is required.
        known = dict(mixed_console.COMBINED_EVIDENCE[0])
        known.update(KNOWN_EVIDENCE)
        printed = []
        with mock.patch.object(
                mixed_console, "COMBINED_EVIDENCE",
                mixed_console.COMBINED_EVIDENCE + [known]):
            mixed_console.MixedConsole().run(
                resource_key, Logger(min_level="error"), printed.append)
        require_known_results(self, printed, with_range=False)

    def test_cloud_countries_console(self):
        if not resource_key:
            self.skipTest(NO_COUNTRIES_KEY)
        from fiftyone_ipintelligence_examples.cloud import countries_console
        evidence = countries_console.EVIDENCE_VALUES + [{
            Constants.EVIDENCE_QUERY_CLIENT_IP_KEY:
                known_address.COUNTRIES_ADDRESS}]
        printed = []
        with mock.patch.object(countries_console, "EVIDENCE_VALUES", evidence):
            countries_console.CountriesConsole().run(
                resource_key, Logger(min_level="error"), printed.append)
        # Every address gets its list, which needs a key carrying the
        # translated country names.
        output = "\n".join(printed)
        self.assertEqual(
            output.count(countries_console.LIST_HEADING), len(evidence),
            output)
        # The known address is in at least one country, with its weighting.
        results = known_address.results_for(
            printed, known_address.COUNTRIES_ADDRESS)
        self.assertIsNotNone(
            results,
            "The example printed no results for "
            f"{known_address.COUNTRIES_ADDRESS}.\n{output}")
        self.assertRegex(
            results,
            r"Countries the address is in, by weighting:\n\t[^\n]+: \d+%\n",
            "The example should give the countries "
            f"{known_address.COUNTRIES_ADDRESS} is in.\n{output}")


if __name__ == "__main__":
    unittest.main()

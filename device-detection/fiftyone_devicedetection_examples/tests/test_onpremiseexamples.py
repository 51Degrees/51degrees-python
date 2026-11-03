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
from fiftyone_devicedetection_shared.key_utils import KeyUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise.gettingstarted_console import GettingStartedConsole
from fiftyone_devicedetection_examples.onpremise.metadata_console import MetaDataConsole
from fiftyone_devicedetection_examples.onpremise.offlineprocessing import OfflineProcessing
from fiftyone_devicedetection_examples.onpremise.match_metrics import MatchMetricsConsole
from fiftyone_devicedetection_examples.onpremise.datafileupdate_console import DataFileUpdateConsole
from fiftyone_devicedetection_examples.onpremise.datafileupdate_console import UPDATE_EXAMPLE_LICENSE_KEY_NAME


class DeviceDetectionExampleTests(unittest.TestCase):
    # Init method - Set data file for hash examples and aditionally a
    # User-Agents file for the performance example.
    def setUp(self):
        self.data_file = ExampleUtils.find_file("51Degrees-LiteV4.1.hash")
        self.user_agents_file = ExampleUtils.find_file("20000 User Agents.csv")
        self.evidence_file = ExampleUtils.find_file("20000 Evidence Records.yml")
        self.logger = Logger()

    def test_onpremise_getting_started_console(self):
        example = GettingStartedConsole()
        example.run(self.data_file, self.logger, print)

    def test_onpremise_metadata_console(self):
        example = MetaDataConsole()
        example.run(self.data_file, self.logger, print)

    def test_onpremise_failure_to_match(self):
        import fiftyone_devicedetection_examples.onpremise.failuretomatch

    def test_onpremise_match_metrics(self):
        example = MatchMetricsConsole()
        example.run(self.data_file, False, self.logger, print)

    def test_onpremise_datafileupdate_console(self):
        example = DataFileUpdateConsole()
        license_key = KeyUtils.get_named_key(UPDATE_EXAMPLE_LICENSE_KEY_NAME)
        example.run("Enterprise-HashV41.hash", license_key, False, self.logger, print)

    def test_onpremise_offline_processing(self):
        # Only run if environment variable set
        if "run_performance_tests" in os.environ:
            example = OfflineProcessing()
            with open(self.evidence_file, "r") as input:
                with open("./offlineprocessing-output.yml", "w") as output:
                    example.run(self.data_file, input, self.logger, output)
            os.remove("./offlineprocessing-output.yml")

    def test_onpremise_offline_processing_with_tabs(self):
        """Test that offline processing handles tab characters in evidence YAML."""
        from io import StringIO
        evidence_with_tabs = (
            "---\n"
            "header.user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\tChrome 98.0\n"
            "---\n"
            "header.user-agent: Mozilla/5.0 (Linux; Android 11; SM-G991B)\t\tChrome/91.0.4472.120\n"
        )
        example = OfflineProcessing()
        output = StringIO()
        example.run(self.data_file, StringIO(evidence_with_tabs), self.logger, output)
        result = output.getvalue()
        self.assertIn("device.ismobile", result)

    def test_onpremise_performance(self):
        # Only run if environment variable set
        if "run_performance_tests" in os.environ:
            import fiftyone_devicedetection_examples.onpremise.performance

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
import shutil
import tempfile
import unittest
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise.gettingstarted_console import GettingStartedConsole
from fiftyone_devicedetection_examples.onpremise.metadata_console import MetaDataConsole
from fiftyone_devicedetection_examples.onpremise.offlineprocessing import OfflineProcessing
from fiftyone_devicedetection_examples.onpremise.match_metrics import MatchMetricsConsole
from fiftyone_devicedetection_examples.onpremise.datafileupdate_console import DataFileUpdateConsole

from .data_update_standin import newer_copy, read_published, serving
from .live_cloud import is_set

# Set to run the performance tests.
RUN_PERFORMANCE_TESTS = "_51DEGREES_RUN_PERFORMANCE_TESTS"

# The fetched data file the update example updates.
TAC_DATAFILE_NAME = "TAC-HashV41.hash"

# The products the stand-in's licence key holds, the second being the
# product of the TAC data file.
STAND_IN_PRODUCTS = ("V4Enterprise", "V4TAC")

# A made-up licence key, which is all the stand-in needs, so the tests never
# use a real one.
MADE_UP_LICENSE_KEY = "MADE-UP-LICENCE-KEY-FOR-THE-STAND-IN"


class DeviceDetectionExampleTests(unittest.TestCase):
    # Init method - Set data file for hash examples and the evidence file
    # for the offline processing example.
    def setUp(self):
        self.data_file = ExampleUtils.find_file("51Degrees-LiteV4.1.hash")
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

    def update_from_stand_in(self, product):
        """Runs the data file update example against the stand-in, which
        serves a copy of the fetched TAC data file with its published date a
        day later. Gives the requests the stand-in received, the published
        date of the file the example updated, and the date it should hold."""
        source = ExampleUtils.find_file(TAC_DATAFILE_NAME)
        self.assertIsNotNone(
            source, f"{TAC_DATAFILE_NAME} is missing. CI's fetch-assets "
            "script puts it in place.")
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, TAC_DATAFILE_NAME)
            shutil.copyfile(source, target)
            served = os.path.join(folder, "served.hash")
            expected = newer_copy(source, served)
            with serving(STAND_IN_PRODUCTS, served) as stand_in:
                DataFileUpdateConsole().run(
                    target, MADE_UP_LICENSE_KEY, False, self.logger, print,
                    product)
            return stand_in.requests, read_published(target), expected

    def test_onpremise_datafileupdate_console_with_product(self):
        # The product given is the one asked for, from the first request.
        requests, published, expected = self.update_from_stand_in("V4TAC")
        self.assertEqual(("V4TAC", 200), requests[0], requests)
        self.assertEqual(expected, published)

    def test_onpremise_datafileupdate_console_without_product(self):
        # With no product given, the first request names none and gets the
        # list of products, and the second asks for the product of the data
        # file in use.
        requests, published, expected = self.update_from_stand_in(None)
        self.assertEqual((None, 300), requests[0], requests)
        self.assertEqual(("V4TAC", 200), requests[1], requests)
        self.assertEqual(expected, published)

    def test_onpremise_datafileupdate_programmatic(self):
        # The update the example asks for itself, which needs no licence
        # key, as the application already holds the new data.
        printed = []
        DataFileUpdateConsole().update_programmatically(
            self.data_file, printed.append)
        shown = "\n".join(printed)
        self.assertIn("A programmatic update needs no licence key", shown)
        self.assertIn(
            "gave the status UpdateStatus.AUTO_UPDATE_SUCCESS", shown)
        self.assertIn("file published on", shown)

    def test_onpremise_offline_processing(self):
        # Only run if environment variable set
        if is_set(RUN_PERFORMANCE_TESTS):
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
        if is_set(RUN_PERFORMANCE_TESTS):
            import fiftyone_devicedetection_examples.onpremise.performance

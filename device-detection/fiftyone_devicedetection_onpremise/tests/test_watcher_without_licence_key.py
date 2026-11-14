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
import threading
import unittest

from fiftyone_pipeline_engines.datafile_update_service import \
    DataFileUpdateService, UpdateStatus
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import \
    DeviceDetectionOnPremisePipelineBuilder

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"

# How often the watcher looks at the file in these tests.
WATCHER_INTERVAL_SECONDS = 0.5

# The longest the tests wait for the watcher to see a replaced file and the
# engine to reload it, set well above a reload of the Lite file on the
# slowest runner.
RELOAD_WAIT_SECONDS = 120


class WatcherWithoutLicenceKeyTests(unittest.TestCase):
    """!
    The file system watcher downloads nothing, so it needs no licence key.
    A key is needed only for automatic updates and the update on start-up,
    which download.
    """

    def setUp(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.path = os.path.join(folder, "51Degrees-LiteV4.1.hash")
        shutil.copyfile(data_file, self.path)

    def build(self, **settings):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=self.path,
            usage_sharing=False,
            performance_profile="MaxPerformance",
            **settings).build()
        self.addCleanup(pipeline.close)
        return pipeline

    def test_the_watcher_runs_with_no_licence_key(self):
        pipeline = self.build(file_system_watcher=True)
        watched = pipeline.get_element("device").data_file
        self.assertTrue(watched.file_system_watcher)
        self.assertFalse(watched.auto_update)
        self.assertFalse(watched.update_on_start)

    def test_a_replaced_file_is_loaded_with_no_licence_key(self):
        service = DataFileUpdateService()
        service.FILE_SYSTEM_WATCHER_INTERVAL_SECONDS = \
            WATCHER_INTERVAL_SECONDS
        statuses = []
        reloaded = threading.Event()

        def on_complete(status, watched):
            statuses.append(status)
            reloaded.set()

        service.on_complete(on_complete)
        pipeline = self.build(
            file_system_watcher=True, data_file_update_service=service)

        # Replace the file, and move its time on so that a file system
        # that keeps times to the second still sees a change.
        shutil.copyfile(data_file, self.path)
        later = os.stat(self.path).st_mtime + 10
        os.utime(self.path, (later, later))

        self.assertTrue(
            reloaded.wait(RELOAD_WAIT_SECONDS),
            "The watcher did not report the replaced file.")
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], statuses)

        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("header.user-agent", mobile_ua)
            flowdata.process()
            self.assertTrue(flowdata.device.ismobile.value())

    def test_a_download_still_needs_a_licence_key(self):
        for setting in ("auto_update", "update_on_start"):
            with self.subTest(setting=setting):
                with self.assertRaises(Exception) as caught:
                    self.build(file_system_watcher=True, **{setting: True})
                self.assertIn("licence key is required", str(caught.exception))

    def test_an_empty_licence_key_turns_the_downloads_off(self):
        pipeline = self.build(
            licence_keys="", auto_update=True, update_on_start=True,
            file_system_watcher=True)
        watched = pipeline.get_element("device").data_file
        self.assertFalse(watched.auto_update)
        self.assertFalse(watched.update_on_start)
        self.assertTrue(watched.file_system_watcher)

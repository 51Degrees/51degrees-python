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
import threading
import unittest

from fiftyone_pipeline_engines.datafile_update_service import \
    DataFileUpdateService, UpdateStatus
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import \
    IpIntelligenceOnPremisePipelineBuilder

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()

# How often the watcher looks at the file in these tests.
WATCHER_INTERVAL_SECONDS = 0.5

# The longest the tests wait for the watcher to see a changed file and the
# engine to reload it, set well above a reload of the Lite file on the
# slowest runner.
RELOAD_WAIT_SECONDS = 120


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the _51DEGREES_IPI_PATH environment variable." % data_file)
class WatcherWithoutLicenceKeyTests(unittest.TestCase):
    """!
    The file system watcher downloads nothing, so it needs no licence key.
    A key is needed only for automatic updates and the update on start-up,
    which download.
    """

    def build(self, **settings):
        pipeline = IpIntelligenceOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            **settings).build()
        self.addCleanup(pipeline.close)
        return pipeline

    def test_the_watcher_runs_with_no_licence_key(self):
        pipeline = self.build(file_system_watcher=True)
        watched = pipeline.get_element("ip").data_file
        self.assertTrue(watched.file_system_watcher)
        self.assertFalse(watched.auto_update)
        self.assertFalse(watched.update_on_start)

    def test_a_changed_file_is_loaded_with_no_licence_key(self):
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

        # The data file can be large, so it is marked as written to by
        # moving its time on rather than copied, and its time is put back
        # afterwards.
        before = os.stat(data_file)
        self.addCleanup(
            os.utime, data_file, (before.st_atime, before.st_mtime))
        later = before.st_mtime + 10
        os.utime(data_file, (later, later))

        self.assertTrue(
            reloaded.wait(RELOAD_WAIT_SECONDS),
            "The watcher did not report the changed file.")
        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], statuses)

        with pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("query.client-ip", "8.8.8.8")
            flowdata.process()
            self.assertEqual({}, flowdata.errors)

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
        watched = pipeline.get_element("ip").data_file
        self.assertFalse(watched.auto_update)
        self.assertFalse(watched.update_on_start)
        self.assertTrue(watched.file_system_watcher)

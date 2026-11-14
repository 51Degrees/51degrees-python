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
from unittest import mock

from fiftyone_pipeline_engines.datafile import DataFile
from fiftyone_pipeline_engines.datafile_update_service import \
    DataFileUpdateService, UpdateStatus
from fiftyone_pipeline_engines.engine import Engine


class RecordingEngine(Engine):
    """An engine that keeps the identifier of each refresh it is asked
    for."""

    def __init__(self):
        super(RecordingEngine, self).__init__()
        self.datakey = "recording"
        self.refreshed = []

    def refresh(self, identifier):
        self.refreshed.append(identifier)


class DataFileRefreshTests(unittest.TestCase):
    """A DataFile with no refresh of its own refreshes its engine, with its
    own identifier when it is given none, which is how the data update
    service calls it."""

    def setUp(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.path = os.path.join(folder, "data.dat")
        with open(self.path, "w") as file:
            file.write("version 1")
        self.engine = RecordingEngine()
        self.data_file = DataFile(
            flow_element=self.engine, identifier="Recording",
            path=self.path, auto_update=False, file_system_watcher=True,
            create_temp_copy=False)

    def test_a_watched_change_refreshes_the_engine(self):
        service = DataFileUpdateService()
        statuses = []
        service.on_complete(
            lambda status, data_file: statuses.append(status))

        # The test makes the watcher's check itself, so no timer runs.
        with mock.patch.object(threading, "Timer"):
            service.register_data_file(self.data_file)
            later = os.stat(self.path).st_mtime + 10
            os.utime(self.path, (later, later))
            service.track_local_data_file_changes(self.data_file)
        service.unregister_data_file(self.data_file)

        self.assertEqual([UpdateStatus.AUTO_UPDATE_SUCCESS], statuses)
        self.assertEqual(["Recording"], self.engine.refreshed)

    def test_an_identifier_given_is_passed_on(self):
        self.data_file.refresh("Other")
        self.assertEqual(["Other"], self.engine.refreshed)

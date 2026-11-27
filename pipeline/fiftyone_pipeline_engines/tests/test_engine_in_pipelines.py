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
An engine with a data file in several Pipelines. Its data file is
registered with one data update service, so it is checked, downloaded and
refreshed once rather than once for each Pipeline.
"""

import unittest
from unittest import mock

from fiftyone_pipeline_core.pipeline import Pipeline
from fiftyone_pipeline_engines.datafile_update_service import \
    DataFileUpdateService
from fiftyone_pipeline_engines.engine import Engine

from .test_datafile_update_http import HttpDataFile


class DataFileEngine(Engine):

    def __init__(self):
        super(DataFileEngine, self).__init__(HttpDataFile())
        self.datakey = "datafile"

    def process_internal(self, flowdata):
        pass


class EngineInPipelinesTests(unittest.TestCase):

    def registrations(self, build):
        """The update services the data file was registered with while
        build ran."""
        services = []
        original = DataFileUpdateService.register_data_file

        def register(service, data_file):
            services.append(service)
            return original(service, data_file)

        with mock.patch.object(
                DataFileUpdateService, "register_data_file", register):
            build()
        return services

    def test_the_data_file_is_registered_once_for_every_pipeline(self):
        engine = DataFileEngine()
        self.addCleanup(engine.close)
        pipelines = []

        def build():
            for _ in range(2):
                pipelines.append(
                    Pipeline([engine], auto_close_elements=False))

        services = self.registrations(build)
        self.assertEqual([pipelines[0].data_file_update_service], services)

    def test_a_data_file_closed_with_its_engine_is_registered_again(self):
        engine = DataFileEngine()
        self.addCleanup(engine.close)
        Pipeline([engine]).close()
        pipelines = []

        def build():
            pipelines.append(Pipeline([engine]))

        services = self.registrations(build)
        self.assertEqual([pipelines[0].data_file_update_service], services)
        self.assertTrue(engine.data_file.registered)


class StartUpErrorTests(unittest.TestCase):
    """!
    An error the errors table does not name, raised by the update on
    start-up while a Pipeline is built. The error reaches the caller, so
    the Pipeline is never made. resource-cleanup.md says "There MUST be
    some mechanism to clean up system resources", so closing the engine
    still stops its data file's checks.
    """

    def failing_engine(self):
        engine = DataFileEngine()
        self.addCleanup(engine.close)
        data_file = engine.data_file
        data_file.update_on_start = True
        data_file.updated_on_start = False
        data_file.auto_update = True

        def update_url():
            raise ValueError("the update URL could not be made")

        data_file.get_update_url = update_url
        return engine

    def test_closing_the_engine_stops_the_checks_after_a_failed_build(self):
        engine = self.failing_engine()
        with self.assertRaises(ValueError):
            Pipeline([engine])
        engine.close()
        timer = getattr(engine.data_file, "update_timer", None)
        if timer is not None:
            timer.join(5)
            self.assertFalse(timer.is_alive())

    def test_a_failed_build_leaves_the_data_file_unregistered(self):
        engine = self.failing_engine()
        with self.assertRaises(ValueError):
            Pipeline([engine])
        self.assertFalse(engine.data_file.registered)


if __name__ == "__main__":
    unittest.main()

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

"""A programmatic update, which the application asks for itself. The data
update service's update_from_memory is the only way an application hands the
engine data it already has, and it needs the engine's data file, so the
engine has one whether or not automatic updates, the update on start-up or
the file system watcher are on."""

import os
import unittest

from fiftyone_pipeline_engines.datafile_update_service import     DataFileUpdateService, UpdateStatus
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import     IpIntelligenceOnPremisePipelineBuilder

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'. Run ci/fetch-assets.ps1 "
    "or set the _51DEGREES_IPI_PATH environment variable." % data_file)
class ProgrammaticUpdateTests(unittest.TestCase):
    """!
    An update the application asks for, with no automatic update of any kind.
    """

    def setUp(self):
        self.service = DataFileUpdateService()
        self.pipeline = IpIntelligenceOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            auto_update=False,
            update_on_start=False,
            file_system_watcher=False,
            data_file_update_service=self.service).build()
        self.addCleanup(self.pipeline.close)
        self.element = self.pipeline.get_element("ip")

    def test_the_engine_has_a_data_file_with_no_automatic_update(self):
        kept = self.element.data_file
        self.assertIsNotNone(kept)
        self.assertFalse(kept.auto_update)
        self.assertFalse(kept.update_on_start)
        self.assertFalse(kept.file_system_watcher)
        self.assertTrue(kept.registered)

    def test_an_update_from_memory_refreshes_the_engine(self):
        with open(data_file, "rb") as new_data:
            data = new_data.read()
        self.assertEqual(
            UpdateStatus.AUTO_UPDATE_SUCCESS,
            self.service.update_from_memory(self.element.data_file, data))
        with self.pipeline.create_flowdata() as flowdata:
            flowdata.evidence.add("query.client-ip", "8.8.8.8")
            flowdata.process()
            self.assertEqual({}, flowdata.errors)


if __name__ == "__main__":
    unittest.main()

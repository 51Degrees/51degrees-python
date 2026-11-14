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

import unittest

from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import IpIntelligenceOnPremise
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


class LicenceKeyRuleTests(unittest.TestCase):
    """!
    data-updates.md lines 107 to 109 and 392. A licence key is needed only
    by polling (auto_update) and the update on start-up, which download from
    the Distributor, and the build fails naming the option to turn off when
    one of them is on with no key. The file system watcher needs no key.
    """

    def build(self, **options):
        engine = IpIntelligenceOnPremise(data_file_path=data_file, **options)
        self.addCleanup(engine.close)
        return engine

    def test_no_key_is_needed_when_nothing_downloads(self):
        for key in (None, ""):
            with self.subTest(key=key):
                engine = self.build(
                    licence_keys=key,
                    auto_update=False,
                    update_on_start=False,
                    file_system_watcher=True)
                self.assertFalse(engine.data_file.auto_update)
                self.assertFalse(engine.data_file.update_on_start)
                self.assertTrue(engine.data_file.file_system_watcher)

    def test_no_key_is_needed_with_the_engine_defaults(self):
        self.build()

    def test_a_download_with_no_key_is_refused_naming_the_option(self):
        cases = [
            (None, {"auto_update": True}, "(auto_update)"),
            ("", {"auto_update": True}, "(auto_update)"),
            ("", {"update_on_start": True}, "(update_on_start)"),
            ("", {"auto_update": True, "update_on_start": True},
                "(auto_update, update_on_start)")]
        for key, options, named in cases:
            with self.subTest(key=key, options=options):
                with self.assertRaises(Exception) as context:
                    self.build(licence_keys=key, **options)
                message = str(context.exception)
                self.assertIn(named, message)
                self.assertIn("require a licence key", message)
                self.assertIn("to False", message)

    def test_the_pipeline_builder_needs_no_key_by_default(self):
        pipeline = IpIntelligenceOnPremisePipelineBuilder(
            data_file_path=data_file, usage_sharing=False).build()
        self.addCleanup(pipeline.close)
        self.assertIn("ip", pipeline.flow_elements_list)

    def test_an_update_url_other_than_the_distributor_needs_no_key(self):
        engine = self.build(
            data_update_url="https://updates.example.com/data.ipi",
            auto_update=True)
        self.assertTrue(engine.data_file.auto_update)


if __name__ == "__main__":
    unittest.main()

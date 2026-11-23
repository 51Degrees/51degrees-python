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

"""The on-premise web examples build their pipelines from config.json, which
must place a Sequence Element before the JSON Builder, or the JSON Builder
fails on every request. Only the pipeline core elements of each file are
built, so no data file is needed."""

import json
import unittest
from pathlib import Path

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

EXAMPLES = Path(__file__).resolve().parent.parent.joinpath(
    "src", "fiftyone_devicedetection_examples", "onpremise")
WEB_EXAMPLES = ("gettingstarted_web", "useragentclienthints_web")
CORE = "fiftyone_pipeline_core."


class WebExampleConfigTests(unittest.TestCase):

    def test_json_builder_has_a_sequence_number(self):
        for example in WEB_EXAMPLES:
            with self.subTest(example):
                config = json.loads(
                    EXAMPLES.joinpath(example, "config.json").read_text())
                options = config["PipelineOptions"]
                options["Elements"] = [
                    element for element in options["Elements"]
                    if element["elementPath"].startswith(CORE)]
                pipeline = PipelineBuilder().build_from_configuration(config)
                self.addCleanup(pipeline.close)
                flowdata = pipeline.create_flowdata()
                flowdata.evidence.add("header.user-agent", "a browser")
                flowdata.process()

                self.assertEqual({}, flowdata.errors)
                self.assertIn(
                    "json", flowdata.get("jsonbundler").as_dictionary())


if __name__ == "__main__":
    unittest.main()

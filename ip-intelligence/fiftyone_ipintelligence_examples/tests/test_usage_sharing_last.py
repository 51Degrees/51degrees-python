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
The IP Intelligence builder, given a data file, puts the usage sharing
element after every other Flow Element, those the caller adds once the
builder is made included, as the country translation examples do. The
fiftyone_ipintelligence package has no tests of its own, so its builder is
tested here.
"""

import unittest

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.onpremise.countries_pipeline import add_country_translation
from fiftyone_ipintelligence_shared.example_constants import ASN_DATAFILE_NAME

DATA_FILE = ExampleUtils.find_file(ASN_DATAFILE_NAME)


@unittest.skipUnless(DATA_FILE, "The free ASN data file was not found.")
class UsageSharingLastTests(unittest.TestCase):

    def datakeys(self, builder):
        pipeline = builder.build()
        self.addCleanup(pipeline.close)
        return [element.datakey for element in pipeline.flow_elements]

    def builder(self, **settings):
        return IpIntelligencePipelineBuilder(
            data_file_path=DATA_FILE, licence_keys="",
            performance_profile="LowMemory", auto_update=False, **settings)

    def test_usage_sharing_is_last(self):
        self.assertEqual(
            ["sequence", "ip", "jsonbundler", "javascriptbuilder",
             "set-headers", "shareusage"],
            self.datakeys(self.builder()))

    def test_usage_sharing_follows_the_country_translation_engines(self):
        self.assertEqual(
            ["sequence", "ip", "countrynames", "countrynamestranslated",
             "jsonbundler", "javascriptbuilder", "set-headers",
             "shareusage"],
            self.datakeys(add_country_translation(self.builder())))

    def test_no_usage_sharing_when_it_is_off(self):
        self.assertEqual(
            ["sequence", "ip", "jsonbundler", "javascriptbuilder",
             "set-headers"],
            self.datakeys(self.builder(usage_sharing=False)))


if __name__ == "__main__":
    unittest.main()

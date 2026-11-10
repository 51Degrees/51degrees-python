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

"""The engine reads each property by its index in the list of names it was
built with, with the native engine and the data file the tests use."""

import os
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import \
    IpIntelligenceOnPremise

from .constants import TestConstants

data_file = TestConstants.get_data_file_path()


def shown(value):
    """What a caller sees of a value, whether or not it has one."""
    if value.has_value():
        return ("value", value.value())
    return ("no value", value.no_value_message())


def process(engine):
    pipeline = PipelineBuilder({
        "add_javascript_builder": False,
        "use_setheader_properties": False}).add(engine).build()
    flowdata = pipeline.create_flowdata()
    flowdata.evidence.add("query.client-ip", "8.8.8.8")
    flowdata.process()
    return pipeline, flowdata


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'." % data_file)
class ReadByIndexTests(unittest.TestCase):

    def test_an_engine_with_no_names_is_built_with_the_data_sets_names(self):
        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="")
        expected = engine.available_property_names(engine.engine)
        self.assertEqual(expected, engine.build_property_names)
        self.assertEqual(
            [name.lower() for name in expected],
            sorted(engine.property_indexes,
                   key=engine.property_indexes.get))

    def test_names_in_another_order_read_the_same_values(self):
        everything = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="")
        names = everything.build_property_names[:6]
        reversed_engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="",
            restricted_properties=list(reversed(names)))
        first, all_data = process(everything)
        second, reversed_data = process(reversed_engine)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertEqual(
            [name.lower() for name in reversed(names)],
            sorted(reversed_engine.property_indexes,
                   key=reversed_engine.property_indexes.get))
        for name in names:
            self.assertEqual(
                shown(all_data.ip.get(name)),
                shown(reversed_data.ip.get(name)), name)


if __name__ == "__main__":
    unittest.main()

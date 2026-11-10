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

"""An engine built with a list of property names reads each one by its
index in that list, with the native engine and the data file the tests use.
An engine built with no names is not covered, because it keeps reading by
name until the native change lands."""

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


def data_set_names(engine):
    """The names the data set holds, in the data set's own order. Only the
    tests use this order, to build engines whose name lists differ from it.
    """
    metadata = engine.engine.getMetaData().getProperties()
    return [metadata.getByIndex(x).getName()
            for x in range(metadata.getSize())
            if metadata.getByIndex(x).getAvailable()]


@unittest.skipUnless(
    os.path.isfile(data_file),
    "No IP intelligence data file found at '%s'." % data_file)
class ReadByIndexTests(unittest.TestCase):

    def names_from_the_data_set(self):
        """The first few property names the data set holds, read from an
        engine built with no names, which still lists them all."""
        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="")
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        return data_set_names(engine), flowdata

    def test_an_engine_with_no_names_keeps_reading_by_name(self):
        """An engine built with no names has an empty table, so nothing
        about it changes until the native change lands."""
        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="")
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        self.assertEqual([], engine.build_property_names)
        self.assertEqual({}, engine.property_indexes)
        # Reading still works, by name, exactly as before.
        self.assertTrue(flowdata.ip.get(data_set_names(engine)[0]))

    def test_the_table_follows_the_order_the_names_were_given_in(self):
        names, _ = self.names_from_the_data_set()
        given = list(reversed(names[:6]))
        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="",
            restricted_properties=list(given))
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        # The index of each name is its place in the list given, not the
        # data set's order.
        for index, name in enumerate(given):
            self.assertEqual(index, engine.property_indexes[name.lower()],
                             name)

    def test_names_in_another_order_read_the_same_values(self):
        names, all_data = self.names_from_the_data_set()
        chosen = names[:6]
        reversed_engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="",
            restricted_properties=list(reversed(chosen)))
        second, reversed_data = process(reversed_engine)
        self.addCleanup(second.close)
        self.addCleanup(reversed_data.close)
        for name in chosen:
            self.assertEqual(
                shown(all_data.ip.get(name)),
                shown(reversed_data.ip.get(name)), name)

    def test_a_superset_data_set_keeps_each_build_time_index(self):
        """The engine is built with a short list of names and the data set
        holds many more, which is the superset case. Each name keeps its
        place in the list given, and reads the value the data set holds."""
        names, all_data = self.names_from_the_data_set()
        self.assertGreater(len(names), 6, "data set must hold a superset")
        chosen = list(reversed(names[:6]))
        engine = IpIntelligenceOnPremise(
            data_file_path=data_file, licence_keys="",
            restricted_properties=list(chosen))
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        for index, name in enumerate(chosen):
            self.assertEqual(index, engine.property_indexes[name.lower()],
                             name)
            self.assertEqual(
                shown(all_data.ip.get(name)),
                shown(flowdata.ip.get(name)), name)


if __name__ == "__main__":
    unittest.main()

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
index in that list, with the native engine and the Lite data file. Also
prints how long a read by name and a read by index take. An engine built
with no names takes the names the native code gives after the first load as
its list, and reads by index too."""

import time
import unittest
import warnings

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
             "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
             "/11D167 Safari/9537.53")
# Reads timed for the figures in the warnings.
TIMED_READS = 20000
# Builds of the index table timed for the figures in the warnings.
TIMED_TABLE_BUILDS = 200


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
    flowdata.evidence.add("header.user-agent", mobile_ua)
    flowdata.process()
    return pipeline, flowdata


def first_places(names):
    """Each name in lower case against its first place in the list, which
    is the index the native code gives."""
    indexes = {}
    for index, name in enumerate(names):
        indexes.setdefault(name.lower(), index)
    return indexes


def data_set_names(engine):
    """The names the data set holds, in the data set's own order. Only the
    tests use this order, to build engines whose name lists differ from it.
    """
    metadata = engine.engine.getMetaData().getProperties()
    return [metadata.getByIndex(x).getName()
            for x in range(metadata.getSize())
            if metadata.getByIndex(x).getAvailable()]


class ReadByIndexTests(unittest.TestCase):

    def names_from_the_data_set(self):
        """The property names the data set holds, read from an engine built
        with no names, which still lists them all."""
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        return data_set_names(engine), flowdata

    def no_names_engine(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        return engine, pipeline, flowdata

    def test_an_engine_with_no_names_reads_by_index(self):
        """An engine built with no names takes the names the native code
        gives after the first load as its list, so its table holds every
        one of them and each index names its property."""
        engine, _, flowdata = self.no_names_engine()
        required = list(engine.engine.getRequiredProperties())
        self.assertIn("IsMobile", required)
        self.assertEqual(first_places(required), engine.property_indexes)
        results = flowdata.device.swig_results
        for name, index in engine.property_indexes.items():
            self.assertEqual(name, results.getPropertyName(index).lower())
        # Reading through the table gives what an engine built with the
        # same names gives.
        named = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            restricted_properties=list(required))
        second, named_data = process(named)
        self.addCleanup(second.close)
        self.addCleanup(named_data.close)
        for name in ("ismobile", "browsername", "platformname"):
            self.assertEqual(
                shown(named_data.device.get(name)),
                shown(flowdata.device.get(name)), name)
        self.assertTrue(flowdata.device.ismobile.value())

    def test_a_reload_keeps_the_table_of_an_engine_with_no_names(self):
        """A reload leaves an engine built with no names with its table,
        and each index still names the same property."""
        engine, pipeline, _ = self.no_names_engine()
        required = list(engine.engine.getRequiredProperties())
        table = dict(engine.property_indexes)
        self.assertEqual(first_places(required), table)
        engine.engine.refreshData()
        self.assertEqual(required, list(engine.engine.getRequiredProperties()))
        self.assertEqual(table, engine.property_indexes)
        flowdata = pipeline.create_flowdata()
        self.addCleanup(flowdata.close)
        flowdata.evidence.add("header.user-agent", mobile_ua)
        flowdata.process()
        results = flowdata.device.swig_results
        for name, index in table.items():
            self.assertEqual(name, results.getPropertyName(index).lower())
        self.assertTrue(flowdata.device.ismobile.value())

    def test_an_engine_with_no_names_times_each_read(self):
        """With no names, a read by name, a read by index and the typed
        read give the same value, with the time each read takes and the
        time to build the index table, for the figures."""
        engine, _, flowdata = self.no_names_engine()
        results = flowdata.device.swig_results
        index = list(engine.engine.getRequiredProperties()).index("IsMobile")
        self.assertEqual(
            results.getValueAsBool("IsMobile").getValue(),
            results.getValueAsBool(index).getValue())
        self.assertEqual(
            results.getValueAsBool("IsMobile").getValue(),
            flowdata.device.ismobile.value())

        start = time.perf_counter()
        for _ in range(TIMED_READS):
            results.getValueAsBool("IsMobile")
        by_name = time.perf_counter() - start
        start = time.perf_counter()
        for _ in range(TIMED_READS):
            results.getValueAsBool(index)
        by_index = time.perf_counter() - start
        start = time.perf_counter()
        for _ in range(TIMED_READS):
            flowdata.device.get("ismobile")
        typed = time.perf_counter() - start
        start = time.perf_counter()
        for _ in range(TIMED_TABLE_BUILDS):
            engine.read_property_indexes()
        table = time.perf_counter() - start
        warnings.warn(
            f"No names, IsMobile read {TIMED_READS} times, native by name "
            f"{by_name * 1e9 / TIMED_READS:.0f} ns a read, native by index "
            f"{by_index * 1e9 / TIMED_READS:.0f} ns a read, typed read "
            f"{typed * 1e9 / TIMED_READS:.0f} ns a read, index table "
            f"{table * 1e9 / TIMED_TABLE_BUILDS:.0f} ns a build")

    def test_the_table_follows_the_order_the_names_were_given_in(self):
        names, _ = self.names_from_the_data_set()
        given = list(reversed(names[:6]))
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
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
        reversed_engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            restricted_properties=list(reversed(chosen)))
        second, reversed_data = process(reversed_engine)
        self.addCleanup(second.close)
        self.addCleanup(reversed_data.close)
        for name in chosen:
            self.assertEqual(
                shown(all_data.device.get(name)),
                shown(reversed_data.device.get(name)), name)

    def test_a_superset_data_set_keeps_each_build_time_index(self):
        """The engine is built with a short list of names and the data set
        holds many more, which is the superset case. Each name keeps its
        place in the list given, and reads the value the data set holds."""
        names, all_data = self.names_from_the_data_set()
        self.assertGreater(len(names), 6, "data set must hold a superset")
        chosen = list(reversed(names[:6]))
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            restricted_properties=list(chosen))
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        for index, name in enumerate(chosen):
            self.assertEqual(index, engine.property_indexes[name.lower()],
                             name)
            self.assertEqual(
                shown(all_data.device.get(name)),
                shown(flowdata.device.get(name)), name)

    def test_a_read_by_name_and_by_index_give_the_same_value_and_time(self):
        """A read by name, a read by index and the typed read all give the
        same value, with the time each read takes for the figures."""
        names, _ = self.names_from_the_data_set()
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            restricted_properties=list(names))
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        results = flowdata.device.swig_results
        index = engine.property_indexes["ismobile"]
        self.assertEqual(
            results.getValueAsBool("IsMobile").getValue(),
            results.getValueAsBool(index).getValue())
        self.assertEqual(
            results.getValueAsBool("IsMobile").getValue(),
            flowdata.device.ismobile.value())

        start = time.perf_counter()
        for _ in range(TIMED_READS):
            results.getValueAsBool("IsMobile")
        by_name = time.perf_counter() - start
        start = time.perf_counter()
        for _ in range(TIMED_READS):
            results.getValueAsBool(index)
        by_index = time.perf_counter() - start
        # The typed read is the whole path a caller takes, through the
        # table and on to the native getter.
        start = time.perf_counter()
        for _ in range(TIMED_READS):
            flowdata.device.get("ismobile")
        typed = time.perf_counter() - start
        warnings.warn(
            f"IsMobile read {TIMED_READS} times, native by name "
            f"{by_name * 1e9 / TIMED_READS:.0f} ns a read, native by index "
            f"{by_index * 1e9 / TIMED_READS:.0f} ns a read, typed read "
            f"{typed * 1e9 / TIMED_READS:.0f} ns a read")


if __name__ == "__main__":
    unittest.main()

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
built with, with the native engine and the Lite data file. Also prints how
long a read by name and a read by index take."""

import time
import unittest
import warnings

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise
from fiftyone_devicedetection_onpremise.DeviceDetectionHashEngineModule \
    import (ConfigHashSwig, EngineHashSwig, EvidenceDeviceDetectionSwig,
            RequiredPropertiesConfigSwig, VectorStringSwig)

data_file = "../../cxx/data/device-detection/51Degrees-LiteV4.1.hash"
mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) "
             "AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile"
             "/11D167 Safari/9537.53")
# Reads and processes timed for the figures in the warnings.
TIMED_READS = 20000
TIMED_PROCESSES = 2000


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


class ReadByIndexTests(unittest.TestCase):

    def test_an_engine_with_no_names_is_built_with_the_data_sets_names(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        expected = engine.available_property_names(engine.engine)
        self.assertEqual(expected, engine.build_property_names)
        self.assertEqual(
            [name.lower() for name in expected],
            sorted(engine.property_indexes,
                   key=engine.property_indexes.get))

    def test_names_in_another_order_read_the_same_values(self):
        everything = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        first, all_data = process(everything)
        self.addCleanup(first.close)
        self.addCleanup(all_data.close)
        names = everything.build_property_names[:6]
        reversed_engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False,
            restricted_properties=list(reversed(names)))
        second, reversed_data = process(reversed_engine)
        self.addCleanup(second.close)
        self.addCleanup(reversed_data.close)
        self.assertEqual(
            [name.lower() for name in reversed(names)],
            sorted(reversed_engine.property_indexes,
                   key=reversed_engine.property_indexes.get))
        for name in names:
            self.assertEqual(
                shown(all_data.device.get(name)),
                shown(reversed_data.device.get(name)), name)

    def test_a_read_by_name_and_by_index_give_the_same_value_and_time(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
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
        warnings.warn(
            f"IsMobile read {TIMED_READS} times, by name "
            f"{by_name * 1e9 / TIMED_READS:.0f} ns a read, by index "
            f"{by_index * 1e9 / TIMED_READS:.0f} ns a read")


    def test_the_cost_of_building_with_every_name(self):
        """Build and process time for an engine given no names, before (an
        empty list, as before this change) and after (every name in the data
        set, read first from a low memory engine)."""

        engine = DeviceDetectionOnPremise(
            data_file_path=data_file, licence_keys="", auto_update=False)
        pipeline, flowdata = process(engine)
        self.addCleanup(pipeline.close)
        self.addCleanup(flowdata.close)
        names = engine.build_property_names
        figures = {}
        for label in ("before", "after"):
            start = time.perf_counter()
            vector = VectorStringSwig()
            if label == "after":
                probe_config = ConfigHashSwig()
                probe_config.setLowMemory()
                probe = EngineHashSwig(
                    data_file, probe_config,
                    RequiredPropertiesConfigSwig(VectorStringSwig()))
                engine.available_property_names(probe)
                del probe
                for name in names:
                    vector.append(name)
            built = EngineHashSwig(
                data_file, engine.config, RequiredPropertiesConfigSwig(vector))
            build = time.perf_counter() - start
            start = time.perf_counter()
            for _ in range(TIMED_PROCESSES):
                evidence = EvidenceDeviceDetectionSwig()
                evidence["header.user-agent"] = mobile_ua
                built.process(evidence).getValueAsBool("IsMobile")
            process_time = time.perf_counter() - start
            figures[label] = (build, process_time)
            del built
        warnings.warn(
            "Engine given no names, before: build "
            f"{figures['before'][0] * 1e3:.1f} ms, process "
            f"{figures['before'][1] * 1e6 / TIMED_PROCESSES:.1f} us. After: "
            f"build {figures['after'][0] * 1e3:.1f} ms, process "
            f"{figures['after'][1] * 1e6 / TIMED_PROCESSES:.1f} us")


if __name__ == "__main__":
    unittest.main()

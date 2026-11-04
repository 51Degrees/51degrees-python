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

# Fails a test that leaves the native results or engine of an on-premise
# engine alive, because they hold the engine's data in memory. The same
# file is in each test folder that runs on-premise engines.
#
# Reference counting frees a native object as soon as nothing holds it. A
# FlowData refers to itself through its evidence, and a pipeline through
# its elements, so when they are not closed only the cycle collector frees
# what they hold. The collector is off while each test runs, so whatever
# the test leaves open is still alive when it ends. Objects that existed
# before the test, such as a pipeline built in setUpClass, are checked once
# every test has run.

import gc
import importlib

import pytest

# The SWIG modules of the on-premise engines, whichever are installed.
NATIVE_MODULES = [
    "fiftyone_devicedetection_onpremise.DeviceDetectionHashEngineModule",
    "fiftyone_ipintelligence_onpremise.IpIntelligenceEngineModule",
]


def _native_types():
    types = []
    for name in NATIVE_MODULES:
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        types.append(module.ResultsBaseSwig)
        types.append(module.EngineBaseSwig)
    return tuple(types)


NATIVE_TYPES = _native_types()

# A failed test is not reported again, because its traceback can hold the
# objects it would have closed.
_failed_tests = set()

# Objects created when the tests were collected are checked at the end only
# when every test ran, because the teardown that closes them runs with the
# tests.
_some_tests_deselected = False


def _alive():
    # The real type is used, because isinstance also asks the object for
    # its __class__, which some proxies cannot answer.
    return [o for o in gc.get_objects()
            if issubclass(type(o), NATIVE_TYPES)]


def _describe(names):
    return (f"{len(names)} native object(s) still alive "
            f"({', '.join(sorted(names))}). Close every FlowData and "
            "pipeline the test creates, for example with a with "
            "statement, so their native data is released straight away.")


def pytest_runtest_logreport(report):
    if report.failed:
        _failed_tests.add(report.nodeid)


def pytest_deselected(items):
    global _some_tests_deselected
    _some_tests_deselected = True


@pytest.fixture(autouse=True)
def native_objects_released(request):
    gc.collect()
    before = {id(o) for o in _alive()}
    gc.disable()
    try:
        yield
        left = [type(o).__name__ for o in _alive() if id(o) not in before]
    finally:
        gc.enable()
    gc.collect()
    if left and request.node.nodeid not in _failed_tests:
        pytest.fail(_describe(left), pytrace=False)


def pytest_sessionfinish(session, exitstatus):
    gc.collect()
    left = [type(o).__name__ for o in _alive()]
    if (left and exitstatus == pytest.ExitCode.OK and
            not _some_tests_deselected):
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(
                "After the last test, " + _describe(left), red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED

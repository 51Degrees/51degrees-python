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

# The tests that call the live cloud service are marked live here, so the
# released test files stay as they are. ci/run-integration-tests.ps1 leaves
# the live tests out when no resource key is passed, and the other tests run.

from pathlib import Path

import pytest
from _pytest.mark.expression import Expression

TESTS = Path(__file__).resolve().parent / "tests"

# Every test in these modules is live.
LIVE_MODULES = {
    TESTS / "test_cloudexamples.py",
    TESTS / "test_cloudgettingstartedweb.py",
}

BUILT_AT_IMPORT = {TESTS / "test_cloudgettingstartedweb.py"}


def _is_live(item):
    return Path(item.path).resolve() in LIVE_MODULES


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: calls the live 51Degrees cloud service and needs a resource "
        "key")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    # Runs before -m deselects, so the selection sees the marker.
    for item in items:
        if _is_live(item):
            item.add_marker(pytest.mark.live)


def _leaves_out_live(config):
    """Whether the -m expression leaves out a test marked live alone."""
    expression = config.getoption("markexpr")
    return bool(expression) and not Expression.compile(expression).evaluate(
        lambda name, **kwargs: name == "live")


# A module that builds a cloud Pipeline when imported raises with no resource
# key, so it is not collected when the live tests are left out. Every test in
# it is live, so the selection is the same.
def pytest_ignore_collect(collection_path, config):
    if (Path(collection_path).resolve() in BUILT_AT_IMPORT and
            _leaves_out_live(config)):
        return True
    return None

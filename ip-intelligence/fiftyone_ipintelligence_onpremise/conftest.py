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

# Every warning the test run raises is an error when
# _51DEGREES_WARNINGS_AS_ERRORS is "true", ignoring case, as it is in the
# builds 51Degrees runs: Python's own (DeprecationWarning, ResourceWarning and
# the rest), pytest's, and those of the packages the tests use. A run anywhere
# else shows them and goes on. setup.py reads the same variable for the native
# build.

import os


def pytest_configure(config):
    if os.environ.get("_51DEGREES_WARNINGS_AS_ERRORS", "").lower() == "true":
        config.addinivalue_line("filterwarnings", "error")

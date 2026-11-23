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

# The markers that keep the live cloud tests out of the unit test run.
# pipeline/ci/run-unit-tests.ps1 deselects "live", and
# pipeline/ci/run-integration-tests.ps1 runs "live and not tier", because no
# key for another tier reaches it. The Cloud 51Did workflow runs the tier
# tests with the Basic key.


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: calls the live 51Degrees cloud service and needs a resource "
        "key")
    config.addinivalue_line(
        "markers",
        "tier: asserts what a key on one tier is entitled to, and needs the "
        "key for that tier")

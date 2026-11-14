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
The mixed console ends with its "Find out more" section when it stops early,
as it does after a run. These run it to each early end, so they need no key
and no network.
"""

from fiftyone_pipeline_examples.cloud.mixed import gettingstarted_console
from fiftyone_pipeline_examples.example_utils import ExampleUtils

# Every name a key is read from.
KEY_SETTINGS = [
    ExampleUtils.RESOURCE_KEY_ENV_VAR,
    ExampleUtils.LEGACY_RESOURCE_KEY_ENV_VAR,
    ExampleUtils.LICENSE_KEY_ENV_VAR,
    ExampleUtils.LEGACY_LICENSE_KEY_ENV_VAR,
]


def test_without_a_key(monkeypatch, capsys):
    for name in KEY_SETTINGS:
        monkeypatch.delenv(name, raising=False)

    gettingstarted_console.main([])

    printed = capsys.readouterr().out
    assert "Find out more:" in printed
    for _, url in gettingstarted_console.GettingStartedConsole.FIND_OUT_MORE:
        assert url in printed


def test_when_the_pipeline_cannot_be_built(monkeypatch, capsys):
    # Stands in for a key the cloud service refuses, or one that carries
    # none of the properties the example shows.
    def refuse(*args, **kwargs):
        raise ValueError("The key carries none of the properties.")

    monkeypatch.setattr(gettingstarted_console, "create_pipeline", refuse)

    gettingstarted_console.main(["a-resource-key"])

    assert "Find out more:" in capsys.readouterr().out

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

"""!
The scripts built into the package, which are the scripts folder of the
derived-properties submodule. The tests run against the package tox
installs from a wheel, so they also prove the wheel carries the scripts.
"""

import os
import re

import pytest

import fiftyone_pipeline_derivedproperty as package
from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElementBuilder, ScriptValidationError,
    builtin_script_names)
from fiftyone_pipeline_derivedproperty.script_set import BUILT_IN_FOLDER

from .helpers import SUBMODULE


def test_the_built_in_scripts_are_the_scripts_of_the_submodule():
    folder = os.path.join(SUBMODULE, "scripts")
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(folder)
                   if re.search(r"\.(ya?ml|json)$", f, re.IGNORECASE))
    assert names
    assert builtin_script_names() == names
    for name in names:
        with open(os.path.join(folder, name + ".yaml"),
                  encoding="utf-8") as source, \
                open(os.path.join(BUILT_IN_FOLDER, name + ".yaml"),
                     encoding="utf-8") as carried:
            assert carried.read() == source.read()


def test_the_package_reads_the_scripts_it_carries():
    assert BUILT_IN_FOLDER.startswith(
        os.path.dirname(os.path.abspath(package.__file__)))


def test_every_built_in_script_has_the_shared_cases():
    for name in builtin_script_names():
        assert os.path.exists(
            os.path.join(SUBMODULE, "tests", name + ".cases.yaml"))


def test_one_element_runs_every_built_in_script():
    builder = DerivedPropertyElementBuilder()
    for name in builtin_script_names():
        builder.add_built_in_script(name)
    element = builder.build()
    assert [s.name for s in element.scripts] == builtin_script_names()
    assert [s.source for s in element.scripts] == [
        "built in " + name for name in builtin_script_names()]


def test_built_in_names_ignore_case():
    element = (DerivedPropertyElementBuilder()
               .add_built_in_script("humanCONFIDENCE").build())
    assert element.scripts[0].name == "HumanConfidence"


def test_an_unknown_built_in_script_names_the_ones_there_are():
    with pytest.raises(ScriptValidationError, match=re.escape(
            "there is no script called 'Nope' in this package. The scripts "
            "in this package are " + ", ".join(builtin_script_names()) +
            ". A script from your own environment is added with "
            "script_files rather than scripts")):
        DerivedPropertyElementBuilder().add_built_in_script("Nope").build()

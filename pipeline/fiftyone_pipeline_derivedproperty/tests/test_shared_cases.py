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
Runs every case file of the derived-properties submodule, which every
language runs, so that this package gives the same answer as the
reference tools, .NET, Rust and PHP for every case.
"""

import os
import re

import pytest

from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElementBuilder, ScriptValidationError)
from fiftyone_pipeline_derivedproperty.evaluate import evaluate
from fiftyone_pipeline_derivedproperty.jsvalues import js_string
from fiftyone_pipeline_derivedproperty.parse import parse
from fiftyone_pipeline_derivedproperty.script_set import ScriptSet

from .helpers import SUBMODULE, SourceElement, pipeline_of, processed

TESTS = os.path.join(SUBMODULE, "tests")
INVALID = os.path.join(TESTS, "invalid")


def _read(path):
    with open(path, encoding="utf-8") as file:
        return parse(file.read()).document


def _value_cases():
    cases = []
    for file in sorted(os.listdir(TESTS)):
        if not file.endswith(".cases.yaml"):
            continue
        document = _read(os.path.join(TESTS, file))
        for case in document["Cases"]:
            cases.append(pytest.param(
                document["Script"], case,
                id=document["Script"] + ": " + case["Name"]))
    return cases


def _rejection_cases():
    return [pytest.param(_read(os.path.join(INVALID, file)), id=file)
            for file in sorted(os.listdir(INVALID))
            if re.search(r"\.ya?ml$", file, re.IGNORECASE)]


def _names_in(message):
    """! The source property names a no value message gives. """
    return [name.lower() for name in re.findall(
        r"'([A-Za-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*)' \(", message)]


_elements = {}


def _element_for(name):
    if name not in _elements:
        _elements[name] = (DerivedPropertyElementBuilder()
                           .add_built_in_script(name).build())
    return _elements[name]


def _run(element, case, wrap):
    """!
    Runs one case through a pipeline. Each element data key the script
    reads gets an element listing every property the script reads under
    that key, holding the values the case gives.
    """
    script = element.scripts[0]
    by_key = {}

    def entry_for(written):
        key, name = written.split(".")
        entry = by_key.setdefault(key.lower(), {"names": [], "values": {}})
        return entry, name

    for prop in script.properties:
        entry, name = entry_for(prop.name)
        entry["names"].append(name)
    for written, value in (case.get("Properties") or {}).items():
        entry, name = entry_for(written)
        entry["values"][name] = value
    sources = [SourceElement(key, entry["values"], entry["names"], wrap)
               for key, entry in by_key.items()]
    flowdata = processed(pipeline_of(sources + [element]))
    return flowdata.get("derived").get(script.output["Name"])


@pytest.mark.parametrize("wrap", [True, False],
                         ids=["as AspectPropertyValues", "as plain values"])
@pytest.mark.parametrize("name, case", _value_cases())
def test_every_value_case(name, case, wrap):
    element = _element_for(name)
    value = _run(element, case, wrap)
    reference = evaluate(element.scripts[0], case.get("Properties"))
    expect = case["Expect"]
    if "Value" in expect:
        assert value.has_value(), value.no_value_message()
        assert js_string(value.value()) == js_string(expect["Value"])
    else:
        assert not value.has_value()
        expected = sorted(p.lower() for p in expect["Missing"])
        assert sorted(_names_in(value.no_value_message())) == expected
        # The element reads each value as the reference tools do, so it
        # gives the reference message word for word.
        assert value.no_value_message() == reference.message
        with pytest.raises(Exception, match=re.escape(reference.message)):
            value.value()


@pytest.mark.parametrize("document", _rejection_cases())
def test_every_rejection_case_is_refused(document):
    script_set = ScriptSet()
    script_set.add_text(document.get("Name"), document["Script"], "case")
    with pytest.raises(ScriptValidationError) as raised:
        script_set.compile()
    paths = [fault.path for fault in raised.value.faults]
    messages = [fault.message for fault in raised.value.faults]
    for expected in (document.get("Expect") or {}).get("Paths") or []:
        assert expected in paths, messages
    for fragment in (document.get("Expect") or {}).get("Mentions") or []:
        assert any(fragment in message for message in messages), messages

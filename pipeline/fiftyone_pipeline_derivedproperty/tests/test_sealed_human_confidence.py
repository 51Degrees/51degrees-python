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
A request that carries a sealed Human Confidence result, being a non-empty
query.humanconfidence, gives HumanConfidence Medium and
HumanConfidenceSource Active. The element can't redeem the sealed result,
so it never gives a High or Low worked out from other properties, as the
Human Confidence page of the pipeline specification asks. Every other
request is unchanged.
"""

import os

import pytest

from fiftyone_pipeline_derivedproperty import DerivedPropertyElementBuilder
from fiftyone_pipeline_derivedproperty.parse import parse

from .helpers import SUBMODULE, SourceElement, band_script, pipeline_of

SEALED = "sealed-result-0123456789"


def _cases_giving_high_or_low():
    path = os.path.join(SUBMODULE, "tests", "HumanConfidence.cases.yaml")
    with open(path, encoding="utf-8") as file:
        document = parse(file.read()).document
    cases = [case for case in document["Cases"]
             if case["Expect"].get("Value") in ("High", "Low")]
    assert cases
    return [pytest.param(case, id=case["Name"]) for case in cases]


def _process(elements, evidence):
    # Errors are raised, not kept, so any error fails the test.
    pipeline = pipeline_of(elements, suppress_process_exceptions=False)
    flowdata = pipeline.create_flowdata()
    for key, value in evidence.items():
        flowdata.evidence.add(key, value)
    flowdata.process()
    return flowdata


def _built_in(case, evidence):
    element = (DerivedPropertyElementBuilder()
               .add_built_in_script("HumanConfidence").build())
    by_key = {}
    for prop in element.scripts[0].properties:
        key, name = prop.name.split(".")
        by_key.setdefault(key.lower(), ([], {}))[0].append(name)
    for written, value in (case.get("Properties") or {}).items():
        key, name = written.split(".")
        by_key.setdefault(key.lower(), ([], {}))[1][name] = value
    sources = [SourceElement(key, values, names)
               for key, (names, values) in by_key.items()]
    return _process(sources + [element], evidence)


def _assert_medium_and_active(flowdata):
    assert flowdata.derived.HumanConfidence.value() == "Medium"
    assert flowdata.derived.get("HumanConfidenceSource").value() == "Active"
    assert dict(flowdata.errors) == {}


@pytest.mark.parametrize("case", _cases_giving_high_or_low())
def test_a_sealed_result_gives_medium_and_active(case):
    _assert_medium_and_active(
        _built_in(case, {"query.humanconfidence": SEALED}))


@pytest.mark.parametrize("case", _cases_giving_high_or_low())
def test_without_a_sealed_result_the_value_is_unchanged(case):
    for evidence in ({}, {"query.humanconfidence": ""},
                     {"header.humanconfidence": SEALED}):
        flowdata = _built_in(case, evidence)
        assert (flowdata.derived.HumanConfidence.value()
                == case["Expect"]["Value"])
        assert "humanconfidencesource" not in flowdata.derived.contents


def test_the_evidence_key_is_matched_without_regard_to_case():
    element = (DerivedPropertyElementBuilder()
               .add_script("HumanConfidence",
                           band_script("HumanConfidence", "source.Count"))
               .build())
    _assert_medium_and_active(_process(
        [SourceElement("source", {"Count": 12}), element],
        {"Query.HumanConfidence": SEALED}))


def test_an_element_without_human_confidence_is_unchanged():
    element = (DerivedPropertyElementBuilder()
               .add_script("Band", band_script("Band", "source.Count"))
               .build())
    flowdata = _process([SourceElement("source", {"Count": 12}), element],
                        {"query.humanconfidence": SEALED})
    assert flowdata.derived.Band.value() == "High"
    assert sorted(flowdata.derived.contents) == ["band"]

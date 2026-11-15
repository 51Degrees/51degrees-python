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
A derived property element is in one pipeline only. The properties it
gives are those of every derived property element in its pipeline, so a
second pipeline would change what the first one reports. The element is
small, so a second pipeline is refused, as multi-pipeline-elements.md
allows, rather than keeping its state for each pipeline.
"""

import pytest

from fiftyone_pipeline_core.pipeline import Pipeline

from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElementBuilder, PipelineConfigurationError)

from .helpers import SourceElement, band_script

ONE_PIPELINE = (
    "This derived property element is already in a pipeline. An element "
    "can be in one pipeline only, as the properties it gives depend on "
    "the other derived property elements in its pipeline. Build another "
    "element for this pipeline.")


def derived(name):
    return (DerivedPropertyElementBuilder()
            .add_script(name, band_script(name, "src.N")).build())


def source():
    return SourceElement("src", {"N": 12})


def test_a_second_pipeline_is_refused():
    element = derived("Demo")
    Pipeline([source(), element])
    with pytest.raises(PipelineConfigurationError) as raised:
        Pipeline([source(), element])
    assert raised.value.faults == [ONE_PIPELINE]


def test_the_refused_pipeline_changes_nothing_the_first_one_gives():
    element = derived("Demo")
    first = Pipeline([source(), element])
    with pytest.raises(PipelineConfigurationError):
        Pipeline([source(), derived("Other"), element])

    assert element.pipelines == [first]
    assert list(element.get_properties()) == ["demo"]
    assert "other" not in first.get_properties()["derived"]
    with first.create_flowdata() as flowdata:
        flowdata.process()
        assert flowdata.derived.get("Demo").value() == "High"


def test_each_pipeline_takes_an_element_of_its_own():
    first = Pipeline([source(), derived("Demo")])
    second = Pipeline([source(), derived("Demo")])
    for pipeline in (first, second):
        with pipeline.create_flowdata() as flowdata:
            flowdata.process()
            assert flowdata.derived.get("Demo").value() == "High"

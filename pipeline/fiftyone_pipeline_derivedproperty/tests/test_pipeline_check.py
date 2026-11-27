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
The checks run when a pipeline adds the element, following
docs/authoring.md of derived-properties, "What the pipeline checks when
the element is added", and the tests of the same check in the .NET, Rust
and PHP elements.
"""

from fiftyone_pipeline_core.pipeline import Pipeline

from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElementBuilder, PipelineConfigurationError)

from .helpers import SourceElement, band_script


def human_confidence():
    return (DerivedPropertyElementBuilder()
            .add_built_in_script("HumanConfidence").build())


def read_by_human_confidence(key):
    names = []
    for prop in human_confidence().scripts[0].properties:
        element_key, name = prop.name.split(".")
        if element_key == key:
            names.append(name)
    return names


def supplier(key, names):
    return SourceElement(key, {}, names)


def derived(scripts):
    builder = DerivedPropertyElementBuilder()
    for name, source in scripts.items():
        builder.add_script(name, band_script(name, source))
    return builder.build()


def needs(script, prop):
    return ("The script '" + script + "' needs the property '" + prop +
            "', and no element in the pipeline supplies it. Either add the "
            "element that supplies '" + prop + "', or change the script so "
            "that it does not name '" + prop + "'.")


def writes(script, output):
    return ("The script '" + script + "' writes the derived property '" +
            output + "', and another element in the pipeline already "
            "writes a property of that name. One pipeline writes each "
            "derived property once.")


def faults(elements):
    """! The faults building a pipeline of the elements gives, or None. """
    try:
        Pipeline(elements)
    except PipelineConfigurationError as error:
        assert str(error) == ("The derived property element cannot be used "
                              "in this pipeline.\n" + "\n".join(error.faults))
        return error.faults
    return None


def test_a_pipeline_supplying_nothing_names_every_property():
    properties = human_confidence().scripts[0].properties
    assert properties
    assert faults([human_confidence()]) == [
        needs("HumanConfidence", p.name) for p in properties]


def test_suppliers_may_sit_anywhere_in_the_pipeline():
    assert faults([
        supplier("device", read_by_human_confidence("device")),
        human_confidence(),
        supplier("ip", read_by_human_confidence("ip"))]) is None
    assert faults([
        human_confidence(),
        supplier("device", read_by_human_confidence("device")),
        supplier("ip", read_by_human_confidence("ip"))]) is None


def test_keys_and_names_are_compared_ignoring_case():
    assert faults([
        supplier("DEVICE",
                 [n.lower() for n in read_by_human_confidence("device")]),
        supplier("Ip", [n.upper() for n in read_by_human_confidence("ip")]),
        human_confidence()]) is None


def test_a_property_listed_under_another_key_is_not_supplied():
    assert faults([
        supplier("device", read_by_human_confidence("device")),
        supplier("location", read_by_human_confidence("ip")),
        human_confidence()]) == [
            needs("HumanConfidence", "ip." + n)
            for n in read_by_human_confidence("ip")]


def test_an_element_listing_no_properties_may_supply_any_of_its_own():
    # A cloud engine learns its properties from the cloud service.
    assert faults([
        supplier("device", read_by_human_confidence("device")),
        supplier("ip", []),
        human_confidence()]) is None
    assert faults([supplier("ip", []), human_confidence()]) == [
        needs("HumanConfidence", "device." + n)
        for n in read_by_human_confidence("device")]


def test_two_elements_writing_one_derived_property_are_refused():
    assert faults([
        supplier("src", ["N"]),
        derived({"Demo": "src.N"}),
        derived({"Demo": "src.N"})]) == [writes("Demo", "Demo")]


def test_a_script_may_read_what_an_earlier_script_of_its_element_writes():
    assert faults([
        supplier("src", ["N"]),
        derived({"Band": "src.N", "BandIsHigh": "derived.Band"})]) is None
    # A later script's property has no value when an earlier one reads it.
    assert faults([
        supplier("src", ["N"]),
        derived({"BandIsHigh": "derived.Band", "Band": "src.N"})]) == [
            needs("BandIsHigh", "derived.Band")]
    # A script's own property is not there when it runs either.
    assert faults([derived({"Demo": "derived.Demo"})]) == [
        needs("Demo", "derived.Demo")]


def test_another_derived_element_supplies_what_it_writes_wherever_it_sits():
    assert faults([
        supplier("src", ["N"]),
        derived({"BandIsHigh": "derived.Band"}),
        derived({"Band": "src.N"})]) is None


def test_properties_written_twice_come_before_those_not_supplied():
    assert faults([
        derived({"Demo": "gone.N"}),
        derived({"Demo": "src.N"})]) == [
            writes("Demo", "Demo"), needs("Demo", "gone.N")]

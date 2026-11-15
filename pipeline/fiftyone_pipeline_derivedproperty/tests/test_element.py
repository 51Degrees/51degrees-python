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
How the element reads the values 51Degrees elements give, writes its
own, logs, takes its settings and describes its properties.
"""

import json
import os
import re

import pytest

from fiftyone_pipeline_core.elementdata_dictionary import ElementDataDictionary
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElement, DerivedPropertyElementBuilder,
    ScriptValidationError)
from fiftyone_pipeline_derivedproperty.evaluate import USUAL_CAUSES

from .helpers import (
    RecordingLogger, SourceElement, band_script, pipeline_of, processed)

BAND_IS_HIGH = "\n".join([
    "Format: 1",
    "Name: BandIsHigh",
    "Version: 1.0.0",
    "Output:",
    "  Name: BandIsHigh",
    "  Description: Whether the band is high.",
    "  ValueType: bool",
    "  IsList: false",
    "Rules:",
    "  - When: { Property: derived.Band, Eq: \"High\" }",
    "    Then: true",
    "  - Else: false"
])

NOT_PRESENT = "property not present on this request"


def band():
    return (DerivedPropertyElementBuilder()
            .add_script("Band", band_script("Band", "src.N")).build())


def band_for(value):
    """! The band written where src.N has a value, given as it is. """
    flowdata = processed(pipeline_of([
        SourceElement("src", {"N": value}, wrap=False), band()]))
    return flowdata.get("derived").get("Band")


def no_band(reason):
    return ("Derived property 'Band' has no value because 1 source property "
            "was not available. 'src.N' (" + reason + "). " + USUAL_CAUSES)


def test_a_value_is_read_under_the_derived_key_whatever_the_case():
    flowdata = processed(pipeline_of([
        SourceElement("src", {"N": 12}), band()]))
    assert flowdata.get("derived").get("Band").value() == "High"
    assert flowdata.get("derived").get("band").value() == "High"
    assert flowdata.derived.BAND.value() == "High"


def test_a_property_that_cannot_be_read_raises_the_message_when_read():
    flowdata = processed(pipeline_of([
        SourceElement("src", {}, ["N"]), band()]))
    value = flowdata.get("derived").get("Band")
    message = no_band("element 'src' has no value for 'N': " + NOT_PRESENT)
    assert not value.has_value()
    assert value.no_value_message() == message
    with pytest.raises(Exception, match=re.escape(message)):
        value.value()


def test_the_reason_an_engine_gives_for_a_property_it_lacks_is_carried():
    class ReasonData(ElementDataDictionary):
        def get(self, key):
            raise Exception(
                "The property " + key + " is not in the resource key.")

    class Engine(SourceElement):
        def process_internal(self, flowdata):
            flowdata.set_element_data(ReasonData(self, {}))

    flowdata = processed(pipeline_of([Engine("src", {}, ["N"]), band()]))
    assert flowdata.get("derived").get("Band").no_value_message() == \
        no_band("element 'src' has no value for 'N': The property N is "
                "not in the resource key.")


def test_a_source_value_with_its_own_message_carries_it():
    assert band_for({"NoValue": "The JavaScript has not run."}) \
        .no_value_message() == no_band(
            "element 'src' has no value for 'N': The JavaScript has not "
            "run.")


def test_a_source_value_with_no_message_reads_as_not_present():
    assert band_for({"NoValue": ""}).no_value_message() == no_band(
        "element 'src' has no value for 'N': " + NOT_PRESENT)


def test_a_weighted_list_gives_the_heaviest_value_the_first_of_two_equal():
    # As on-premise IP Intelligence gives a weighted list.
    assert band_for([{"value": 5, "weighting": 0.2},
                     {"value": 15, "weighting": 0.8}]).value() == "High"
    # As the cloud gives one before it is normalised.
    assert band_for([{"value": 15, "rawweighting": 26214},
                     {"value": 5, "rawweighting": 39321}]).value() == "Low"
    assert band_for([{"value": 15, "weighting": 0.5},
                     {"value": 5, "weighting": 0.5}]).value() == "High"


def test_a_list_that_is_not_weighted_cannot_be_read():
    assert band_for([5, 15]).no_value_message() == no_band(
        "held a list where a single value is needed")


def test_a_value_that_is_not_a_number_cannot_be_read_as_one():
    assert band_for("Unknown").no_value_message() == no_band(
        "held 'Unknown' which cannot be read as int")


def test_no_element_data_for_a_source_is_logged_once():
    # The element supplying src.N runs after the derived property element.
    logger = RecordingLogger()
    pipeline = pipeline_of([band(), SourceElement("src", {"N": 12})], logger)
    first = processed(pipeline)
    processed(pipeline)
    assert not first.get("derived").get("Band").has_value()
    assert logger.messages("error") == [
        "The script 'Band' reads 'src.N', and the request carried no "
        "element data 'src' at all, so the script has no value. The usual "
        "cause is the element that supplies it running after this element "
        "rather than before it. This is reported once."]


def test_building_the_pipeline_logs_what_each_script_produces():
    logger = RecordingLogger()
    pipeline_of([SourceElement("src", {"N": 1}), band()], logger)
    assert ("Derived property script 'Band' version 1.0.0, format 1, from "
            "code, produces 'derived.Band' as string."
            in logger.messages("info"))
    compiled = [m for m in logger.messages("debug") if m.startswith(
        "Derived property script 'Band' compiled to ")][0]
    model = json.loads(compiled[compiled.index("{"):])
    assert model["Properties"] == {"src.N": {"Type": "int"}}
    assert model["Output"]["Dependencies"] == ["src.N"]


def test_a_deprecated_script_logs_a_warning_with_its_note():
    logger = RecordingLogger()
    element = (DerivedPropertyElementBuilder().add_script(
        "Band", band_script("Band", "src.N", extra=(
            "Deprecated: true\nDeprecationNote: Use BandTwo instead.")))
        .build())
    pipeline_of([SourceElement("src", {"N": 1}), element], logger)
    assert logger.messages("warning") == [
        "Derived property script 'Band' is deprecated. Use BandTwo "
        "instead."]


def test_a_later_script_reads_what_an_earlier_one_wrote():
    element = (DerivedPropertyElementBuilder()
               .add_script("Band", band_script("Band", "src.N"))
               .add_script("BandIsHigh", BAND_IS_HIGH)
               .build())
    flowdata = processed(pipeline_of([
        SourceElement("src", {"N": 12}), element]))
    # A bool output is a boolean.
    assert flowdata.get("derived").get("BandIsHigh").value() is True


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "Band.yaml").write_text(band_script("Band", "src.N"))
    (tmp_path / "Other.yaml").write_text(band_script("Other", "src.N"))
    (tmp_path / "notes.txt").write_text("not a script")
    (tmp_path / "with,comma").mkdir()
    (tmp_path / "with,comma" / "Third.yaml").write_text(
        band_script("Third", "src.N"))
    return str(tmp_path)


def test_settings_name_built_in_scripts_and_files_in_any_case(folder):
    element = DerivedPropertyElement(**{
        "Scripts": "isgdpr, HumanConfidence",
        "ScriptFiles": os.path.join(folder, "*.yaml") + ", \"" +
        os.path.join(folder, "with,comma", "Third.yaml") + "\""
    })
    assert [s.name for s in element.scripts] == [
        "IsGdpr", "HumanConfidence", "Band", "Other", "Third"]
    assert element.scripts[0].source == "built in IsGdpr"
    assert element.scripts[2].source == os.path.join(folder, "Band.yaml")


def test_settings_may_be_lists_of_strings(folder):
    element = DerivedPropertyElement(
        scripts=["IsGdpr"], script_files=[os.path.join(folder, "Band.yaml")])
    assert [s.name for s in element.scripts] == ["IsGdpr", "Band"]


def test_a_setting_the_element_does_not_have_is_refused():
    with pytest.raises(ValueError, match=re.escape(
            "The derived property element has no setting 'script'. Its "
            "settings are scripts and script_files.")):
        DerivedPropertyElement(script="IsGdpr")


def test_a_file_or_folder_that_is_not_there_is_a_fault(folder):
    with pytest.raises(ScriptValidationError):
        DerivedPropertyElement(
            script_files=os.path.join(folder, "Missing.yaml"))
    with pytest.raises(ScriptValidationError, match="does not exist"):
        DerivedPropertyElement(
            script_files=os.path.join(folder, "nowhere", "*.yaml"))


def test_a_pipeline_configuration_builds_the_element():
    pipeline = PipelineBuilder().build_from_configuration({
        "PipelineOptions": {
            "Elements": [
                {"elementPath": "tests.country_element",
                 "elementName": "CountryElement"},
                {"elementPath": "fiftyone_pipeline_derivedproperty",
                 "elementName": "DerivedPropertyElement",
                 "elementParameters": {"Scripts": "IsGdpr"}}
            ]
        }
    })
    flowdata = processed(pipeline)
    assert flowdata.get("derived").get("IsGdpr").value() is True


def test_faults_in_every_script_are_reported_together():
    with pytest.raises(ScriptValidationError) as raised:
        (DerivedPropertyElementBuilder()
         .add_script("One", band_script("One", "src.N")
                     .replace("Ge: 10", "Gx: 10"))
         .add_script("Two", band_script("Two", "N"))
         .add_built_in_script("Nothing")
         .build())
    scripts = []
    for fault in raised.value.faults:
        if fault.script not in scripts:
            scripts.append(fault.script)
    assert scripts == ["One", "Two", "Nothing"]
    message = str(raised.value)
    assert "unknown operator 'Gx'" in message
    assert "'N' is not a source property" in message
    assert "there is no script called 'Nothing'" in message


def test_an_element_with_no_script_is_refused():
    with pytest.raises(ValueError,
                       match="At least one script must be configured."):
        DerivedPropertyElement()


def test_two_scripts_in_one_element_cannot_write_one_property():
    builder = (DerivedPropertyElementBuilder()
               .add_script("Band", band_script("Band", "src.N"))
               .add_script("BandTwo", band_script("BandTwo", "src.N")
                           .replace("  Name: BandTwo", "  Name: Band")))
    with pytest.raises(ScriptValidationError, match=re.escape(
            "two scripts in the same element write the property 'Band', "
            "being 'Band' and 'BandTwo'. One element writes each property "
            "once")):
        builder.build()


def test_the_property_metadata_is_the_output_block():
    element = band()
    assert element.get_properties() == {
        "band": {
            "name": "Band",
            "type": "string",
            "category": "Testing",
            "description": "Whether a number is ten or more.",
            "islist": False,
            "dependencies": ["src.N"]
        }
    }
    flowdata = processed(pipeline_of([
        SourceElement("src", {"N": 12}), element]))
    assert list(flowdata.get_where("category", "Testing").keys()) == \
        ["band"]


def test_the_json_bundler_carries_the_values_of_every_derived_element():
    pipeline = pipeline_of([
        SourceElement("src", {"N": 12}),
        band(),
        DerivedPropertyElementBuilder()
        .add_script("BandIsHigh", BAND_IS_HIGH).build()
    ], add_javascript_builder=True, add_javascript_builder_element=False)
    flowdata = processed(pipeline)
    output = flowdata.get("jsonbundler").get("json")
    # Both derived property elements write one element data, and each
    # gives the properties of both.
    assert output["derived"]["band"] == "High"
    assert output["derived"]["bandishigh"] is True
    assert sorted(pipeline.get_element("derived").get_properties()) == \
        ["band", "bandishigh"]


def test_the_element_accepts_no_evidence():
    assert band().get_evidence_key_filter().filter_evidence({
        "header.user-agent": "x", "query.n": "12"}) == {}

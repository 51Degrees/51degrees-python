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
Reading and running scripts, as docs/format-1.md of derived-properties
describes, for the points the case files do not reach, and for the places
where Python's own rules differ from JavaScript's.
"""

import json

from fiftyone_pipeline_derivedproperty.canonical import canonical
from fiftyone_pipeline_derivedproperty.evaluate import USUAL_CAUSES, evaluate
from fiftyone_pipeline_derivedproperty.validate import validate_text


def script_with(condition, value_type="string"):
    then, otherwise = (("true", "false") if value_type == "bool"
                       else ('"Yes"', '"No"'))
    return "\n".join([
        "Format: 1",
        "Name: Demo",
        "Version: 1.0.0",
        "Output:",
        "  Name: Demo",
        "  Description: A demonstration.",
        "  ValueType: " + value_type,
        "  IsList: false",
        "Rules:",
        "  - When: " + condition,
        "    Then: " + then,
        "  - Else: " + otherwise])


def model_of(text):
    model, faults = validate_text(text)
    assert faults == []
    return model


def test_yes_and_no_are_strings_as_the_yaml_core_schema_reads_them():
    model = model_of(script_with("{ Property: src.A, Eq: yes }"))
    assert model.properties[0].type == "string"
    assert evaluate(model, {"src.A": "yes"}).value == "Yes"


def test_a_date_stays_the_text_written():
    model = model_of(script_with("{ Property: src.A, Eq: 2026-11-16 }"))
    assert model.properties[0].type == "string"
    assert evaluate(model, {"src.A": "2026-11-16"}).value == "Yes"


def test_keys_that_differ_only_in_case_are_refused():
    model, faults = validate_text(
        script_with("{ Property: src.A, Eq: 1 }") + "\nname: Demo")
    assert model is None
    assert "differ only in case" in faults[0].message


def test_a_key_written_twice_is_refused():
    model, faults = validate_text(
        script_with("{ Property: src.A, Eq: 1 }") + "\nName: Demo")
    assert model is None
    assert "duplicated mapping key" in faults[0].message


def test_keys_are_matched_without_regard_to_case():
    model = model_of(script_with("{ property: src.A, eq: 1 }")
                     .replace("ValueType", "valuetype")
                     .replace("Rules:", "RULES:"))
    assert evaluate(model, {"SRC.a": 1}).value == "Yes"


def test_a_json_script_gives_the_same_model_as_its_yaml():
    yaml_model = model_of(script_with("{ Property: src.A, Ge: 8 }"))
    json_model = model_of(json.dumps({
        "Format": 1,
        "Name": "Demo",
        "Version": "1.0.0",
        "Output": {
            "Name": "Demo",
            "Description": "A demonstration.",
            "ValueType": "string",
            "IsList": False
        },
        "Rules": [
            {"When": {"Property": "src.A", "Ge": 8.0}, "Then": "Yes"},
            {"Else": "No"}
        ]
    }))
    assert canonical(json_model) == canonical(yaml_model)


def test_a_whole_number_written_with_a_point_still_infers_int():
    model = model_of(script_with("{ Property: src.A, Lt: 2.0 }"))
    assert model.properties[0].type == "int"
    assert evaluate(model, {"src.A": 1.5}).missing == ["src.A"]


def test_a_whole_number_beyond_an_int_infers_double():
    model = model_of(script_with("{ Property: src.A, Lt: 3000000000 }"))
    assert model.properties[0].type == "double"


def test_an_int_is_a_signed_32_bit_whole_number():
    model = model_of(script_with("{ Property: src.A, Ge: 0 }"))
    assert evaluate(model, {"src.A": 2147483647}).value == "Yes"
    assert evaluate(model, {"src.A": -2147483648}).value == "No"
    assert evaluate(model, {"src.A": 2147483648}).missing == ["src.A"]
    assert evaluate(model, {"src.A": {"String": "3000000000"}}).missing == \
        ["src.A"]


def test_a_boolean_is_not_a_number():
    model = model_of(script_with("{ Property: src.A, Eq: 1 }"))
    assert evaluate(model, {"src.A": True}).missing == ["src.A"]
    bool_model = model_of(script_with("{ Property: src.A, Eq: true }"))
    assert evaluate(bool_model, {"src.A": 1}).missing == ["src.A"]


def test_values_that_mean_nothing_never_become_false_or_zero():
    as_bool = model_of(script_with("{ Property: src.A, Eq: false }"))
    as_int = model_of(script_with("{ Property: src.A, Eq: 0 }"))
    for nothing in ["N/A", "Unknown", "", "1", "yes"]:
        assert evaluate(as_bool, {"src.A": nothing}).missing == ["src.A"]
    for nothing in ["N/A", "Unknown", "", "1.0", "١"]:
        assert evaluate(as_int, {"src.A": nothing}).missing == ["src.A"]


def test_a_native_value_read_as_a_string_takes_its_printed_form():
    model = model_of(script_with('{ Property: src.A, In: ["8", "True"] }'))
    assert evaluate(model, {"src.A": 8}).value == "Yes"
    assert evaluate(model, {"src.A": 8.0}).value == "Yes"
    assert evaluate(model, {"src.A": True}).value == "Yes"
    assert evaluate(model, {"src.A": 9}).value == "No"


def test_strings_compare_ordinally_and_with_regard_to_case():
    model = model_of(script_with('{ Property: src.A, StartsWith: "Mob" }'))
    assert evaluate(model, {"src.A": "Mobile"}).value == "Yes"
    assert evaluate(model, {"src.A": "mobile"}).value == "No"


def test_a_list_of_whole_and_decimal_numbers_reads_as_double():
    model = model_of(script_with("{ Property: src.A, In: [1, 2.5] }"))
    assert model.properties[0].type == "double"
    assert evaluate(model, {"src.A": 2.5}).value == "Yes"


def test_every_fault_in_a_script_is_reported_together():
    model, faults = validate_text(
        script_with("{ Property: A, Equals: 1 }")
        .replace("Format: 1", "Format: 2"))
    assert model is None
    paths = [fault.path for fault in faults]
    assert "Format" in paths
    assert "Rules[0].When.Property" in paths


def test_the_message_names_every_missing_property_in_order():
    model = model_of("\n".join([
        "Format: 1",
        "Name: Demo",
        "Version: 1.0.0",
        "Output:",
        "  Name: Demo",
        "  Description: A demonstration.",
        "  ValueType: string",
        "  IsList: false",
        "Checks:",
        "  First: { Property: src.B, Eq: true }",
        "Rules:",
        "  - When: { Property: src.A, Eq: 1 }",
        "    Then: \"Yes\"",
        "  - Else: \"No\""]))
    result = evaluate(model, {"src.A": {"NoValue": "Not today."}})
    assert result.missing == ["src.B", "src.A"]
    assert result.message == (
        "Derived property 'Demo' has no value because 2 source properties "
        "were not available. 'src.B' (element 'src' has no value for 'B': "
        "property not present on this request). 'src.A' (element 'src' has "
        "no value for 'A': Not today.). " + USUAL_CAUSES)


def test_a_value_that_cannot_be_read_is_shown_as_javascript_shows_it():
    model = model_of(script_with('{ Property: src.A, Eq: "x" }'))
    model_int = model_of(script_with("{ Property: src.A, Eq: 1 }"))
    assert "held '1.5' which cannot be read as int" in \
        evaluate(model_int, {"src.A": 1.5}).message
    assert "held 'False' which cannot be read as int" in \
        evaluate(model_int, {"src.A": False}).message
    assert evaluate(model, {"src.A": 8.0}).missing is None


def test_a_bool_output_is_a_boolean():
    model = model_of(script_with("{ Property: src.A, Eq: 1 }", "bool"))
    assert evaluate(model, {"src.A": 1}).value is True
    assert evaluate(model, {"src.A": 2}).value is False


def test_canonical_json_prints_whole_numbers_without_a_point():
    model = model_of(script_with("{ Property: src.A, Lt: 2.0 }"))
    assert '"Lt": 2\n' in canonical(model)

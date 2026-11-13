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
Checks a parsed script against format 1 and turns it into the model the
evaluator runs. Every fault is collected rather than stopping at the
first, so an author sees everything wrong with a file in one go.

Each fault has a path, being a place in the document such as
Rules[3].When.All[1].

This follows tools/validate.mjs of derived-properties function for
function, with the same messages.
"""

import re
from types import SimpleNamespace

from .evaluate import convert_string, INT_MIN, INT_MAX
from .jsvalues import (
    is_bool, is_number, is_whole, is_string, is_list, is_mapping,
    js_string, js_json)
from .parse import parse, line_of, ParseError

## The value types format 1 allows for an output property.
VALUE_TYPES = ["string", "bool", "int", "double"]

## The comparison operators, and the inferred types each is allowed on.
OPERATORS = {
    "Eq": ["bool", "int", "double", "string"],
    "Ne": ["bool", "int", "double", "string"],
    "Gt": ["int", "double"],
    "Ge": ["int", "double"],
    "Lt": ["int", "double"],
    "Le": ["int", "double"],
    "In": ["bool", "int", "double", "string"],
    "NotIn": ["bool", "int", "double", "string"],
    "StartsWith": ["string"],
    "EndsWith": ["string"],
    "Contains": ["string"]
}

## The two counts a rule can compare a group of checks by.
AGGREGATES = ["Passed", "Failed"]

_TOP_LEVEL_KEYS = ["Format", "Name", "Version", "Deprecated",
                   "DeprecationNote", "Output", "Checks", "Rules"]

## The Output keys, in the order the canonical form prints them.
OUTPUT_KEYS = ["Name", "Description", "ValueType", "StoredValueType",
               "DefaultValue", "IsList", "IsMandatory", "IsObsolete",
               "Category", "IsPopular", "ExportValues", "Url",
               "DisplayOrder", "PropertyId", "VendorIds", "Dependencies",
               "Values"]

_OUTPUT_BOOLEANS = ["IsList", "IsMandatory", "IsObsolete", "IsPopular",
                    "ExportValues"]

_OUTPUT_CARRIED = [
    ("Category", "string"),
    ("Url", "string"),
    ("StoredValueType", "string"),
    ("DisplayOrder", "integer"),
    ("PropertyId", "integer"),
    ("VendorIds", "array"),
    ("Dependencies", "array")
]

_IDENTIFIER = "^[A-Za-z][A-Za-z0-9]*$"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\Z")
_SOURCE_PROPERTY = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*\Z")
_SEMANTIC_VERSION = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+(?:\.[0-9A-Za-z.-]+)*)?"
    r"(?:\+[0-9A-Za-z.-]+)?\Z")


class Fault(object):
    """! One thing wrong with a script, and where it is. """

    def __init__(self, script, source, path, line, message):
        self.script = script
        self.source = source
        self.path = path
        self.line = line
        self.message = message

    def __repr__(self):
        return faults_message([self])


class Model(object):
    """! A script once it has been read and validated. """

    def __init__(self, source):
        self.format = None
        self.name = None
        self.version = None
        self.deprecated = False
        self.deprecation_note = None
        self.source = source
        self.output = None
        self.properties = []
        self.checks = []
        self.rules = []


def validate_text(text, name=None, source="code"):
    """!
    Parses and validates script text.

    @param text: the script as YAML or JSON.
    @param name: the file name without its extension, which the script's
        Name must equal, or None for no such check.
    @param source: where the script came from, for the fault messages.
    @return: (model, faults), where model is None when there are faults.
    """
    try:
        parsed = parse(text)
    except ParseError as error:
        return (None, [Fault(name, source, "", error.line, error.message)])
    return validate(parsed, name, source)


def validate(parsed, name=None, source="code"):
    """!
    Validates an already parsed script.

    @return: (model, faults), where model is None when there are faults.
    """
    context = _Context(parsed, name, source)
    model = _build_model(context)
    if context.faults:
        return (None, context.faults)
    return (model, [])


def faults_message(faults):
    """!
    The message an implementation raises when a script does not
    validate, being one line per fault.
    """
    lines = []
    for f in faults:
        where = "(document)" if f.path == "" else f.path
        line = "" if f.line is None else " line " + str(f.line)
        lines.append(
            ("script" if f.script is None else f.script) +
            " (" + f.source + ")" + line + " at " + where + ": " +
            f.message)
    return "\n".join(lines)


# ---------------------------------------------------------------------

class _Context(object):
    def __init__(self, parsed, name, source):
        self.parsed = parsed
        self.document = parsed.document
        self.script = name
        self.source = source
        self.faults = []
        # Where each source property was first seen, its inferred type
        # and the path that inferred it, so a conflict can name both
        # places.
        self.properties = {}

    def fault(self, path, node, message):
        self.faults.append(Fault(
            self.script, self.source, path,
            line_of(self.parsed, node), message))


def _get(mapping, name):
    """! Reads a key from a mapping without regard to case. """
    if not is_mapping(mapping):
        return None
    lower = name.lower()
    for key in mapping.keys():
        if key.lower() == lower:
            return mapping[key]
    return None


def _found(mapping, name):
    """! Whether a key is written, whatever its value. """
    if not is_mapping(mapping):
        return False
    lower = name.lower()
    return any(key.lower() == lower for key in mapping.keys())


def _unknown_keys(mapping, allowed):
    lower = [k.lower() for k in allowed]
    return [k for k in mapping.keys() if k.lower() not in lower]


def _build_model(context):
    document = context.document

    for key in _unknown_keys(document, _TOP_LEVEL_KEYS):
        context.fault(key, document,
                      "unknown key '" + key + "' at the top level. "
                      "Expected one of " + ", ".join(_TOP_LEVEL_KEYS))

    model = Model(context.source)
    model.format = _read_format(context)
    model.name = _read_name(context)
    model.version = _read_version(context)

    _read_deprecation(context, model)
    model.output = _read_output(context)

    # Checks are read before rules so that a rule can reference one.
    check_names = _read_check_names(context)
    _read_checks(context, model, check_names)
    _read_rules(context, model, check_names)
    _finalise_properties(model)
    _compute_dependencies(model)

    return model


# The reference tools tell a key that is not written (undefined) from one
# written as null. Python reads both as None, so where the difference
# changes the message, _found says whether the key was written.

def _read_format(context):
    if not _found(context.document, "Format"):
        context.fault("Format", context.document,
                      "required key 'Format' is missing")
        return None
    value = _get(context.document, "Format")
    if is_bool(value) or value != 1:
        context.fault("Format", context.document,
                      "Format must be 1, found " + js_json(value))
        return None
    return 1


def _read_name(context):
    if not _found(context.document, "Name"):
        context.fault("Name", context.document,
                      "required key 'Name' is missing")
        return None
    value = _get(context.document, "Name")
    if not is_string(value):
        context.fault("Name", context.document,
                      "Name expected a string, found " + _type_of(value))
        return None
    if not _IDENTIFIER_RE.match(value):
        context.fault("Name", context.document,
                      "script name '" + value + "' does not match the "
                      "pattern " + _IDENTIFIER)
        return value
    if context.script is not None and context.script != value:
        context.fault("Name", context.document,
                      "script name '" + value + "' must equal the file "
                      "name '" + context.script + "'")
    return value


def _read_version(context):
    if not _found(context.document, "Version"):
        context.fault("Version", context.document,
                      "required key 'Version' is missing")
        return None
    value = _get(context.document, "Version")
    if not is_string(value) or not _SEMANTIC_VERSION.match(value):
        context.fault("Version", context.document,
                      "Version expected a semantic version such as 1.0.0, "
                      "found " + js_json(value))
        return None
    return value


def _read_deprecation(context, model):
    if _found(context.document, "Deprecated"):
        deprecated = _get(context.document, "Deprecated")
        if not is_bool(deprecated):
            context.fault("Deprecated", context.document,
                          "Deprecated expected a boolean, found " +
                          _type_of(deprecated))
        else:
            model.deprecated = deprecated
    if _found(context.document, "DeprecationNote"):
        note = _get(context.document, "DeprecationNote")
        if not is_string(note):
            context.fault("DeprecationNote", context.document,
                          "DeprecationNote expected a string, found " +
                          _type_of(note))
        else:
            model.deprecation_note = note
    if model.deprecated and not model.deprecation_note:
        context.fault("DeprecationNote", context.document,
                      "a deprecated script must say what to use instead "
                      "in DeprecationNote")
    if not model.deprecated and model.deprecation_note:
        context.fault("DeprecationNote", context.document,
                      "DeprecationNote is only allowed when Deprecated is "
                      "true")


def _read_output(context):
    unknown = context.script if context.script is not None else "unknown"
    if not _found(context.document, "Output"):
        context.fault("Output", context.document,
                      "required key 'Output' is missing")
        return {"Name": unknown, "ValueType": None, "Values": None}
    raw = _get(context.document, "Output")
    if not is_mapping(raw):
        context.fault("Output", context.document,
                      "Output expected a mapping, found " + _type_of(raw))
        return {"Name": unknown, "ValueType": None, "Values": None}
    for key in _unknown_keys(raw, OUTPUT_KEYS):
        context.fault("Output." + key, raw,
                      "unknown key '" + key + "' under Output. A typo in a "
                      "metadata field is a fault rather than a value that "
                      "is quietly dropped")

    output = {}

    # Name.
    if not _found(raw, "Name"):
        context.fault("Output.Name", raw, "required key 'Name' is missing")
    else:
        name = _get(raw, "Name")
        if not is_string(name) or not _IDENTIFIER_RE.match(name):
            context.fault("Output.Name", raw,
                          "Output.Name " + js_json(name) + " does not "
                          "match the pattern " + _IDENTIFIER)
        else:
            output["Name"] = name
    if "Name" not in output:
        output["Name"] = unknown

    # Description.
    if not _found(raw, "Description"):
        context.fault("Output.Description", raw,
                      "required key 'Description' is missing. Say what the "
                      "property asserts, not how far to trust it")
    else:
        description = _get(raw, "Description")
        if not is_string(description) or description.strip() == "":
            context.fault("Output.Description", raw,
                          "Output.Description expected a non empty string, "
                          "found " + _type_of(description))
        else:
            output["Description"] = description

    # ValueType.
    if not _found(raw, "ValueType"):
        context.fault("Output.ValueType", raw,
                      "required key 'ValueType' is missing")
        output["ValueType"] = None
    else:
        value_type = _get(raw, "ValueType")
        if (not is_string(value_type) or
                value_type.lower() not in VALUE_TYPES):
            context.fault("Output.ValueType", raw,
                          "Output.ValueType '" + js_string(value_type) +
                          "' is not allowed in format 1. Expected one of " +
                          ", ".join(VALUE_TYPES))
            output["ValueType"] = None
        else:
            output["ValueType"] = value_type.lower()

    # IsList.
    if not _found(raw, "IsList"):
        context.fault("Output.IsList", raw,
                      "required key 'IsList' is missing")
    else:
        is_list_value = _get(raw, "IsList")
        if not is_bool(is_list_value):
            context.fault("Output.IsList", raw,
                          "Output.IsList expected a boolean, found " +
                          _type_of(is_list_value))
        elif is_list_value is True:
            context.fault("Output.IsList", raw,
                          "Output.IsList must be false in format 1. List "
                          "outputs are deferred")
        else:
            output["IsList"] = False
    if "IsList" not in output:
        output["IsList"] = False

    # Values.
    output["Values"] = None
    if _found(raw, "Values"):
        values = _get(raw, "Values")
        if not is_list(values):
            context.fault("Output.Values", raw,
                          "Output.Values expected a list, found " +
                          _type_of(values))
        elif (output["ValueType"] is not None and
              output["ValueType"] != "string" and
              output["ValueType"] != "int"):
            context.fault("Output.Values", raw,
                          "Output.Values is only allowed where ValueType is "
                          "string or int, not " + output["ValueType"])
        else:
            output["Values"] = _read_values(context, values)

    # Booleans carried through unchanged.
    for key in _OUTPUT_BOOLEANS:
        if key == "IsList" or not _found(raw, key):
            continue
        value = _get(raw, key)
        if not is_bool(value):
            context.fault("Output." + key, raw,
                          "Output." + key + " expected a boolean, found " +
                          _type_of(value))
            continue
        output[key] = value

    # Strings and the remaining fields carried through unchanged.
    for key, kind in _OUTPUT_CARRIED:
        if not _found(raw, key):
            continue
        value = _get(raw, key)
        if kind == "string" and not is_string(value):
            context.fault("Output." + key, raw,
                          "Output." + key + " expected a string, found " +
                          _type_of(value))
            continue
        if kind == "integer" and not is_whole(value):
            context.fault("Output." + key, raw,
                          "Output." + key + " expected an integer, found " +
                          _type_of(value))
            continue
        if kind == "array" and not is_list(value):
            context.fault("Output." + key, raw,
                          "Output." + key + " expected a list, found " +
                          _type_of(value))
            continue
        output[key] = value

    # DefaultValue is the string form of the value, so it is checked
    # against the value type and the value list.
    if _found(raw, "DefaultValue"):
        default_value = _get(raw, "DefaultValue")
        if not is_string(default_value):
            context.fault("Output.DefaultValue", raw,
                          "Output.DefaultValue expected a string holding "
                          "the string form of the value, found " +
                          _type_of(default_value))
        else:
            output["DefaultValue"] = default_value
            if output["ValueType"] is not None:
                if not convert_string(default_value,
                                      output["ValueType"])[0]:
                    context.fault("Output.DefaultValue", raw,
                                  "Output.DefaultValue '" + default_value +
                                  "' cannot be read as " +
                                  output["ValueType"])
            if (output["Values"] is not None and
                    not any(js_string(v["Name"]) == default_value
                            for v in output["Values"])):
                context.fault("Output.DefaultValue", raw,
                              "Output.DefaultValue '" + default_value +
                              "' is not one of the values listed under "
                              "Output.Values")

    return output


def _read_values(context, values):
    result = []
    for index, entry in enumerate(values):
        path = "Output.Values[" + str(index) + "]"
        if not is_mapping(entry):
            context.fault(path, values,
                          "a value expected a mapping of Name and "
                          "Description, found " + _type_of(entry))
            continue
        for key in _unknown_keys(entry, ["Name", "Description"]):
            context.fault(path + "." + key, entry,
                          "unknown key '" + key + "' in a value. Expected "
                          "Name and Description")
        value_name = _get(entry, "Name")
        if not (is_string(value_name) or is_number(value_name)):
            context.fault(path + ".Name", entry, "a value must have a Name")
            continue
        value_description = _get(entry, "Description")
        if (_found(entry, "Description") and
                not is_string(value_description)):
            context.fault(path + ".Description", entry,
                          "a value Description expected a string, found " +
                          _type_of(value_description))
        result.append({
            "Name": value_name,
            "Description": value_description
            if is_string(value_description) else None
        })
    seen = set()
    for entry in result:
        key = js_string(entry["Name"])
        if key in seen:
            context.fault("Output.Values", values,
                          "the value '" + key + "' is listed more than once")
        seen.add(key)
    return result


def _read_check_names(context):
    names = []
    if not _found(context.document, "Checks"):
        return names
    raw = _get(context.document, "Checks")
    if not is_mapping(raw):
        context.fault("Checks", context.document,
                      "Checks expected a mapping of names to conditions, "
                      "found " + _type_of(raw))
        return names
    for name in raw.keys():
        if not _IDENTIFIER_RE.match(name):
            context.fault("Checks." + name, raw,
                          "check name '" + name + "' does not match the "
                          "pattern " + _IDENTIFIER)
            continue
        names.append(name)
    return names


def _read_checks(context, model, check_names):
    raw = _get(context.document, "Checks")
    if not is_mapping(raw):
        return
    for name in check_names:
        condition = _read_condition(
            context, model, raw[name], "Checks." + name, raw, check_names,
            name in raw)
        model.checks.append(SimpleNamespace(name=name, condition=condition))


def _read_rules(context, model, check_names):
    if not _found(context.document, "Rules"):
        context.fault("Rules", context.document,
                      "required key 'Rules' is missing")
        return
    raw = _get(context.document, "Rules")
    if not is_list(raw):
        context.fault("Rules", context.document,
                      "Rules expected a list, found " + _type_of(raw))
        return
    if len(raw) == 0:
        context.fault("Rules", raw, "Rules must hold at least one rule")
        return
    # Every script ends in an Else, so a script always chooses a value
    # once its source properties have been read.
    if not _found(raw[-1], "Else"):
        context.fault("Rules", raw,
                      "the last rule must be an Else, which is what a "
                      "script falls back to when no earlier rule matched")
    for index, entry in enumerate(raw):
        path = "Rules[" + str(index) + "]"
        if not is_mapping(entry):
            context.fault(path, raw,
                          "a rule expected a mapping, found " +
                          _type_of(entry))
            continue
        for key in _unknown_keys(entry, ["When", "Then", "Else"]):
            context.fault(path + "." + key, entry,
                          "unknown key '" + key + "' in a rule. Expected "
                          "When and Then, or Else")
        has_when = _found(entry, "When")
        has_then = _found(entry, "Then")
        has_else = _found(entry, "Else")
        is_last = index == len(raw) - 1

        if has_else and has_when:
            context.fault(path, entry,
                          "a rule has both When and Else. A rule is either "
                          "When with Then, or Else on its own")
            continue
        if has_else and not is_last:
            context.fault(path, entry,
                          "Else is only allowed on the last rule")
            continue
        if not has_else and not has_when:
            context.fault(path, entry,
                          "a rule needs a When, or an Else on the last rule")
            continue
        if has_when and not has_then:
            context.fault(path, entry, "a rule with When needs a Then")
            continue

        value_path = path + (".Else" if has_else else ".Then")
        value = _read_rule_value(
            context, model,
            _get(entry, "Else") if has_else else _get(entry, "Then"),
            value_path, entry)
        when = None
        if has_when:
            when = _read_condition(context, model, _get(entry, "When"),
                                   path + ".When", entry, check_names, True)
        model.rules.append(SimpleNamespace(when=when, value=value))


def _read_rule_value(context, model, raw, path, node):
    """!
    Reads a Then or an Else, which is a literal of Output.ValueType and
    must be one of Output.Values where that list is given.
    """
    value_type = model.output["ValueType"]
    if raw is None:
        context.fault(path, node,
                      "a rule value is a null literal, which format 1 does "
                      "not allow")
        return None
    if is_list(raw) or is_mapping(raw):
        context.fault(path, node,
                      "a rule value is a literal of the output value type, "
                      "found " + _type_of(raw))
        return None
    if value_type is not None:
        literal_type = infer_type(raw)
        if not _literal_matches(literal_type, value_type):
            context.fault(path, node,
                          "expected a " + value_type + " to match "
                          "Output.ValueType, found " + _type_of(raw))
            return None
    values = model.output["Values"]
    if values is not None and not any(
            js_string(v["Name"]) == js_string(raw) for v in values):
        context.fault(path, node,
                      "'" + js_string(raw) + "' is not one of the values "
                      "listed under Output.Values (" +
                      ", ".join(js_string(v["Name"]) for v in values) + ")")
        return None
    return raw


# ---------------------------------------------------------------------
# Conditions.
# ---------------------------------------------------------------------

def _faulted():
    """!
    What a condition that could not be read becomes. A fault has been
    recorded by the time it is returned, so the model is thrown away and
    it is never evaluated.
    """
    return SimpleNamespace(kind="all", items=[])


def _read_condition(context, model, raw, path, parent, check_names,
                    written=True):
    if not is_mapping(raw):
        context.fault(path, parent,
                      "a condition expected a mapping, found " +
                      (_type_of(raw) if written else "nothing"))
        return _faulted()
    keys = list(raw.keys())
    if len(keys) == 0:
        context.fault(path, raw, "a condition is empty")
        return _faulted()
    lower = [k.lower() for k in keys]

    if "property" in lower:
        return _read_comparison(context, model, raw, path)
    if "check" in lower:
        return _read_check_reference(context, raw, path, keys, check_names)
    if any(a.lower() in lower for a in AGGREGATES):
        return _read_aggregate_condition(context, raw, path, keys,
                                         check_names)
    if "all" in lower or "any" in lower:
        which = "All" if "all" in lower else "Any"
        if len(keys) != 1:
            context.fault(path, raw,
                          which + " must be the only key of its condition, "
                          "found " + ", ".join(keys))
        items = _get(raw, which)
        if not is_list(items):
            context.fault(path + "." + which, raw,
                          which + " expected a list of conditions, found " +
                          _type_of(items))
            return _faulted()
        if len(items) == 0:
            context.fault(path + "." + which, raw,
                          which + " must list at least one condition")
            return _faulted()
        return SimpleNamespace(
            kind=which.lower(),
            items=[_read_condition(context, model, item,
                                   path + "." + which + "[" + str(index) +
                                   "]", items, check_names)
                   for index, item in enumerate(items)])
    if "not" in lower:
        if len(keys) != 1:
            context.fault(path, raw,
                          "Not must be the only key of its condition, "
                          "found " + ", ".join(keys))
        return SimpleNamespace(
            kind="not",
            item=_read_condition(context, model, _get(raw, "Not"),
                                 path + ".Not", raw, check_names,
                                 _found(raw, "Not")))
    context.fault(path, raw,
                  "a condition must be a comparison, a Check reference, an "
                  "aggregate, All, Any or Not. Found the keys " +
                  ", ".join(keys))
    return _faulted()


def _operator_named(key):
    for operator in OPERATORS:
        if operator.lower() == key.lower():
            return operator
    return None


def _read_comparison(context, model, raw, path):
    keys = list(raw.keys())
    property_key = next(k for k in keys if k.lower() == "property")
    prop = raw[property_key]
    operator_keys = [k for k in keys if k != property_key]

    if not is_string(prop) or not _SOURCE_PROPERTY.match(prop):
        context.fault(path + ".Property", raw,
                      "'" + js_string(prop) + "' is not a source property. "
                      "Write it as elementKey.PropertyName, for example "
                      "device.IsCrawler")
        return _faulted()
    if len(operator_keys) == 0:
        context.fault(path, raw,
                      "a comparison on '" + prop + "' has no operator. "
                      "Expected exactly one of " + ", ".join(OPERATORS))
        return _faulted()
    known = [k for k in operator_keys if _operator_named(k) is not None]
    for key in operator_keys:
        if key not in known:
            context.fault(path, raw,
                          "unknown operator '" + key + "', expected one of " +
                          ", ".join(OPERATORS))
    if len(known) == 0:
        return _faulted()
    if len(operator_keys) > 1:
        context.fault(path, raw,
                      "a condition takes exactly one operator, found " +
                      ", ".join(operator_keys))
        return _faulted()
    op = _operator_named(known[0])
    operand = raw[known[0]]

    if operand is None:
        context.fault(path + "." + op, raw,
                      "a null literal is not allowed. Give the value to "
                      "compare against")
        return _faulted()

    if op == "In" or op == "NotIn":
        if not is_list(operand):
            context.fault(path + "." + op, raw,
                          op + " expects a list of values, found " +
                          _type_of(operand))
            return _faulted()
        if len(operand) == 0:
            context.fault(path + "." + op, raw,
                          op + " expects a non empty list")
            return _faulted()
        if any(m is None for m in operand):
            context.fault(path + "." + op, raw,
                          "a null literal is not allowed in a list")
            return _faulted()
        member_types = [infer_type(m) for m in operand]
        first = member_types[0]
        # int and double may sit together and the list reads as double.
        numeric = all(t == "int" or t == "double" for t in member_types)
        if not numeric and any(t != first for t in member_types):
            context.fault(path + "." + op, raw,
                          "every member of a list must be of the same type, "
                          "found " +
                          ", ".join("" if t is None else t
                                    for t in member_types))
            return _faulted()
        if not numeric:
            type = first
        elif "double" in member_types:
            type = "double"
        else:
            type = "int"
    else:
        type = infer_type(operand)
        if type is None:
            context.fault(path + "." + op, raw,
                          "the literal " + js_json(operand) + " has no type "
                          "format 1 knows")
            return _faulted()

    if type not in OPERATORS[op]:
        context.fault(path, raw,
                      "operator '" + op + "' is not allowed on type " +
                      js_string(type) + ". It is allowed on " +
                      ", ".join(OPERATORS[op]))
        return _faulted()

    slot = _use_property(context, model, prop, type, path, raw)
    return SimpleNamespace(
        kind="compare", slot=slot, property=prop.lower(),
        propertyName=prop, op=op, operand=operand, type=type)


def _read_check_reference(context, raw, path, keys, check_names):
    if len(keys) != 1:
        context.fault(path, raw,
                      "Check must be the only key of its condition, found " +
                      ", ".join(keys))
    name = _get(raw, "Check")
    if not is_string(name):
        context.fault(path + ".Check", raw,
                      "Check expected the name of a check, found " +
                      _type_of(name))
        return _faulted()
    if name not in check_names:
        context.fault(path + ".Check", raw,
                      "check '" + name + "' is not defined. The checks are " +
                      ("(none)" if len(check_names) == 0
                       else ", ".join(check_names)))
        return _faulted()
    return SimpleNamespace(kind="check", name=name,
                           index=check_names.index(name))


def _read_aggregate_condition(context, raw, path, keys, check_names):
    aggregate_keys = [k for k in keys
                      if any(a.lower() == k.lower() for a in AGGREGATES)]
    if len(aggregate_keys) > 1:
        context.fault(path, raw,
                      "an aggregate condition takes one of " +
                      ", ".join(AGGREGATES) + ", found " +
                      ", ".join(aggregate_keys))
        return _faulted()
    agg = next(a for a in AGGREGATES
               if a.lower() == aggregate_keys[0].lower())
    group = _read_group(context, raw[aggregate_keys[0]], path + "." + agg,
                        raw, check_names)

    operator_keys = [k for k in keys if k != aggregate_keys[0]]
    if len(operator_keys) == 0:
        context.fault(path, raw,
                      "an aggregate condition has no operator. Expected "
                      "exactly one of Eq, Ne, Gt, Ge, Lt, Le")
        return _faulted()
    if len(operator_keys) > 1:
        context.fault(path, raw,
                      "a condition takes exactly one operator, found " +
                      ", ".join(operator_keys))
        return _faulted()
    op = _operator_named(operator_keys[0])
    if op is None:
        context.fault(path, raw,
                      "unknown operator '" + operator_keys[0] + "', expected "
                      "one of Eq, Ne, Gt, Ge, Lt, Le")
        return _faulted()
    if "int" not in OPERATORS[op]:
        context.fault(path, raw,
                      "operator '" + op + "' is not allowed on a count, "
                      "which is an int")
        return _faulted()

    # A count is compared against a whole number and against nothing
    # else.
    operand = raw[operator_keys[0]]
    if not is_whole(operand):
        context.fault(path + "." + op, raw,
                      "an aggregate is compared with a whole number, "
                      "found " + _type_of(operand))
        return _faulted()

    return SimpleNamespace(kind="aggregate", agg=agg, group=group, op=op,
                           operand=operand)


def _read_group(context, raw, path, node, check_names):
    """!
    A group is the word Checks, meaning every named check, or a list of
    check names. It becomes a list of indexes, or None for every check.
    """
    if is_string(raw):
        if raw.lower() == "checks":
            return None
        context.fault(path, node,
                      "a group is the word Checks, meaning every check, or "
                      "a list of check names. Found '" + raw + "'")
        return []
    if is_list(raw):
        indexes = []
        for name in raw:
            if not is_string(name):
                context.fault(path, node,
                              "a group lists check names, found " +
                              _type_of(name))
                continue
            if name not in check_names:
                context.fault(path, node,
                              "check '" + name + "' is not defined. The "
                              "checks are " +
                              ("(none)" if len(check_names) == 0
                               else ", ".join(check_names)))
                continue
            indexes.append(check_names.index(name))
        return indexes
    context.fault(path, node,
                  "a group is the word Checks or a list of check names, "
                  "found " + _type_of(raw))
    return []


# ---------------------------------------------------------------------
# Source properties.
# ---------------------------------------------------------------------

def _use_property(context, model, name, type, path, node):
    """!
    Records that a condition names a source property, and that the
    literal it is compared against infers a type. Returns the slot index
    the evaluator reads the property from.
    """
    key = name.lower()
    entry = context.properties.get(key)
    if entry is None:
        entry = SimpleNamespace(key=key, name=name, type=type,
                                type_path=path, slot=len(model.properties))
        context.properties[key] = entry
        model.properties.append(entry)
        return entry.slot
    if entry.type != type:
        context.fault(path, node,
                      "'" + name + "' is inferred as " + type + " here but "
                      "was already inferred as " + entry.type + " at " +
                      entry.type_path + ". Every use of a property must "
                      "infer the same type")
    return entry.slot


def _finalise_properties(model):
    """! The model exposes the properties without the bookkeeping. """
    model.properties = [SimpleNamespace(key=p.key, name=p.name, type=p.type)
                        for p in model.properties]


def _compute_dependencies(model):
    if model.output.get("Dependencies") is not None:
        return
    model.output["Dependencies"] = [p.name for p in model.properties]


# ---------------------------------------------------------------------
# Literals.
# ---------------------------------------------------------------------

def infer_type(literal):
    """!
    The type a literal in the script infers. A number infers its type
    from the value rather than from the way the value was written, so 8,
    8.0 and 8e0 all infer int. A whole number too large for a signed 32
    bit integer infers double instead.
    """
    if is_bool(literal):
        return "bool"
    if is_number(literal):
        if not is_whole(literal):
            return "double"
        return "int" if INT_MIN <= literal <= INT_MAX else "double"
    if is_string(literal):
        return "string"
    return None


def _literal_matches(literal_type, value_type):
    if literal_type == value_type:
        return True
    # A whole number written without a decimal point reads as a double.
    return literal_type == "int" and value_type == "double"


def _type_of(value):
    if value is None:
        return "a null literal"
    if is_list(value):
        return "a list"
    if is_bool(value):
        return "a boolean"
    if is_number(value):
        return "an integer" if is_whole(value) else "a number"
    if is_string(value):
        return "a string (" + js_json(value) + ")"
    if is_mapping(value):
        return "a mapping"
    return type(value).__name__

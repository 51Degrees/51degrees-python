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
Prints a validated model as canonical JSON, which the element writes to
the debug log at build, so that anyone holding the log can see exactly
what was evaluated without the file. The form is PascalCase keys in the
order of the format reference, two space indent, literal types kept, the
inferred type of each source property and the computed Dependencies list.

This follows tools/canonical.mjs of derived-properties, and prints the
same text.
"""

from .jsvalues import js_json
from .validate import OUTPUT_KEYS


def canonical(model):
    """!
    @param model: a model from validate.py.
    @return: canonical JSON, without a trailing newline.
    """
    return js_json(canonical_object(model), indent=2)


def canonical_object(model):
    """! The canonical form as a dict, before it is printed. """
    result = {
        "Format": model.format,
        "Name": model.name,
        "Version": model.version
    }
    if model.deprecated:
        result["Deprecated"] = True
        result["DeprecationNote"] = model.deprecation_note
    result["Output"] = _canonical_output(model.output)

    # The inferred type of every source property, which the file does not
    # carry because it is worked out from the literals compared against.
    result["Properties"] = {}
    for prop in model.properties:
        result["Properties"][prop.name] = {"Type": prop.type}

    if model.checks:
        result["Checks"] = {}
        for check in model.checks:
            result["Checks"][check.name] = _canonical_condition(
                check.condition, model)

    result["Rules"] = [_canonical_rule(rule, model) for rule in model.rules]
    return result


def _canonical_rule(rule, model):
    if rule.when is None:
        return {"Else": rule.value}
    return {
        "When": _canonical_condition(rule.when, model),
        "Then": rule.value
    }


def _canonical_output(output):
    result = {}
    for key in OUTPUT_KEYS:
        if key == "Values":
            continue
        if output.get(key) is None:
            continue
        result[key] = output[key]
    if output.get("Values") is not None:
        result["Values"] = [
            {"Name": value["Name"]} if value["Description"] is None
            else {"Name": value["Name"], "Description": value["Description"]}
            for value in output["Values"]]
    return result


def _canonical_condition(condition, model):
    kind = condition.kind
    if kind == "compare":
        return {"Property": condition.propertyName,
                condition.op: condition.operand}
    if kind == "check":
        return {"Check": condition.name}
    if kind == "aggregate":
        return {condition.agg: _canonical_group(condition.group, model),
                condition.op: condition.operand}
    if kind == "all":
        return {"All": [_canonical_condition(i, model)
                        for i in condition.items]}
    if kind == "any":
        return {"Any": [_canonical_condition(i, model)
                        for i in condition.items]}
    if kind == "not":
        return {"Not": _canonical_condition(condition.item, model)}
    raise RuntimeError("unknown condition kind '" + kind + "'")


def _canonical_group(group, model):
    if group is None:
        return "Checks"
    return [model.checks[index].name for index in group]

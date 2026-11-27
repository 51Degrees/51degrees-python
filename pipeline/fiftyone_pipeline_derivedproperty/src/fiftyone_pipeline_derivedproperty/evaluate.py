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
The evaluator. Given a validated model and the source property values for
one request, it produces the output value, or the reason there is no
output value.

This follows tools/evaluate.mjs of derived-properties function for
function, with the same messages, so that the conformance cases in that
repository prove it.
"""

import math
import re

from .jsvalues import (
    is_bool, is_number, is_whole, is_string, is_list, is_mapping,
    js_string)

## The sentence appended to every "no value" message, naming the things
# that usually cause a source property to be missing.
USUAL_CAUSES = (
    "Usual causes are the element that supplies the property not being in "
    "the pipeline, or being added after this element rather than before "
    "it, the property being excluded in the engine configuration, the "
    "property not being included in the resource key, or JavaScript that "
    "populates the property not having run yet.")

## The smallest value the type int holds.
INT_MIN = -2147483648
## The largest value the type int holds.
INT_MAX = 2147483647

_NOT_PRESENT = "property not present on this request"
_INT_TEXT = re.compile(r"^[+-]?[0-9]+$")
_DOUBLE_TEXT = re.compile(
    r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


class Result(object):
    """!
    What a script gives for one request, being a value, or the source
    properties that were missing and the message naming them.
    """

    def __init__(self, value=None, has_value=False, missing=None,
                 message=None, trace=None):
        self.value = value
        self.has_value = has_value
        self.missing = missing
        self.message = message
        self.trace = trace


class NoValue(object):
    """!
    A source value that exists but carries a no value message, as a case
    file writes it with { NoValue: "..." }.
    """

    def __init__(self, message):
        self.message = message


def evaluate(model, properties, trace=False):
    """!
    Runs one script for one request.

    @param model: a model from validate.py.
    @param properties: a dict from "element.Property" to a native value, a
        { "String": "..." } dict holding the string form, a
        { "NoValue": "..." } dict or a NoValue standing for a source value
        that exists but carries a no value message, or a list of
        { "Value", "Weight" } dicts. A property that is not a key of the
        dict is absent.
    @param trace: whether to record what was read, which checks passed
        and which rule matched.
    @rtype: Result
    """
    lookup = _build_lookup(properties)
    slots = [_read_slot(p, lookup) for p in model.properties]

    recorded = None
    if trace:
        recorded = {
            "properties": [
                {"name": p.name, "available": slot[0],
                 "value": slot[1] if slot[0] else None, "reason": slot[2]}
                for p, slot in zip(model.properties, slots)],
            "checks": [],
            "matchedRule": None,
            "matchedBy": None
        }

    # Every source property the script names is read before anything is
    # evaluated. A property is either there or it is not, and where any
    # one of them is missing the script says so rather than guessing.
    missing = []
    reasons = []
    for prop, slot in zip(model.properties, slots):
        if not slot[0]:
            missing.append(prop)
            reasons.append(slot[2])
    if missing:
        return Result(
            missing=[p.name for p in missing],
            message=_missing_message(model, missing, reasons),
            trace=recorded)

    state = _State(model, slots)
    for index, check in enumerate(model.checks):
        state.checks[index] = _evaluate_condition(check.condition, state)
        if recorded is not None:
            recorded["checks"].append({
                "name": check.name,
                "state": describe_state(state.checks[index])})

    for index, rule in enumerate(model.rules):
        # An Else rule has no condition and always matches.
        if rule.when is None or _evaluate_condition(rule.when, state):
            if recorded is not None:
                recorded["matchedRule"] = index
                recorded["matchedBy"] = "Else" if rule.when is None else "When"
            return Result(value=rule.value, has_value=True, trace=recorded)

    # Every script ends in an Else, which the validator enforces, so the
    # loop above always returns.
    raise RuntimeError(
        "the rules of '" + model.output["Name"] + "' do not end in an "
        "Else, which format 1 does not allow")


def describe_state(value):
    """! "true" or "false", for the trace. """
    return "true" if value else "false"


class _State(object):
    def __init__(self, model, slots):
        self.model = model
        self.slots = slots
        self.checks = [None] * len(model.checks)


# ---------------------------------------------------------------------
# Reading source properties.
# ---------------------------------------------------------------------

def _build_lookup(properties):
    lookup = {}
    if properties:
        for key, value in properties.items():
            lookup[key.lower()] = value
    return lookup


def _read_slot(prop, lookup):
    """!
    Reads one source property for one request, converting it to the type
    the script inferred for it.

    @return: (available, value, reason)
    """
    dot = prop.name.index(".")
    element_key = prop.name[:dot]
    property_name = prop.name[dot + 1:]

    def absent(reason):
        return (False, None, reason)

    def not_available(detail):
        return absent("element '" + element_key + "' has no value for '" +
                      property_name + "': " + detail)

    if prop.key not in lookup:
        return not_available(_NOT_PRESENT)
    raw = lookup[prop.key]
    if raw is None:
        return not_available(_NOT_PRESENT)
    if isinstance(raw, NoValue):
        return not_available(js_string(raw.message))
    if is_mapping(raw):
        if "NoValue" in raw:
            return not_available(js_string(raw["NoValue"]))
        if "String" in raw:
            raw = raw["String"]
            if raw is None:
                return not_available(_NOT_PRESENT)
    if is_list(raw):
        # A list of weighted values takes the value with the highest
        # weight. Any other list where a single value is needed is invalid.
        weighted = len(raw) > 0 and all(
            is_mapping(m) and "Value" in m for m in raw)
        if not weighted:
            return absent("held a list where a single value is needed")
        best = raw[0]
        for member in raw:
            if _weight(member) > _weight(best):
                best = member
        raw = best["Value"]
        if raw is None:
            return not_available(_NOT_PRESENT)

    converted = convert_value(raw, prop.type)
    if not converted[0]:
        return absent("held '" + _display_raw(raw) +
                      "' which cannot be read as " + prop.type)
    return (True, converted[1], None)


def _weight(member):
    weight = member.get("Weight")
    return weight if is_number(weight) else 0


def _display_raw(raw):
    if is_string(raw):
        return raw
    if is_bool(raw):
        return "True" if raw else "False"
    return js_string(raw)


def _is_int32(value):
    return is_whole(value) and INT_MIN <= value <= INT_MAX


def convert_value(raw, type):
    """!
    Converts a source value, which arrives either as the native type or
    as a string, to the type the script inferred.

    @return: (ok, value)
    """
    if is_string(raw):
        return convert_string(raw, type)
    if type == "bool":
        return (True, raw) if is_bool(raw) else (False, None)
    if type == "int":
        return (True, int(raw)) if _is_int32(raw) else (False, None)
    if type == "double":
        if is_number(raw) and math.isfinite(raw):
            return (True, raw)
        return (False, None)
    if type == "string":
        if is_bool(raw):
            return (True, "True" if raw else "False")
        if is_number(raw):
            return (True, js_string(raw))
        return (False, None)
    return (False, None)


def convert_string(raw, type):
    """!
    Converts the string form of a value to the type given. Values are
    never coerced loosely, so N/A, Unknown and an empty string never
    become false or zero.

    @return: (ok, value)
    """
    if not is_string(raw):
        return (False, None)
    if type == "bool":
        trimmed = raw.strip().lower()
        if trimmed == "true":
            return (True, True)
        if trimmed == "false":
            return (True, False)
        return (False, None)
    if type == "int":
        trimmed = raw.strip()
        if not _INT_TEXT.match(trimmed):
            return (False, None)
        value = int(trimmed)
        return (True, value) if _is_int32(value) else (False, None)
    if type == "double":
        trimmed = raw.strip()
        if not _DOUBLE_TEXT.match(trimmed):
            return (False, None)
        value = float(trimmed)
        return (True, value) if math.isfinite(value) else (False, None)
    if type == "string":
        return (True, raw)
    return (False, None)


# ---------------------------------------------------------------------
# Conditions.
# ---------------------------------------------------------------------

def _evaluate_condition(condition, state):
    """!
    Every condition is true or false, because the rules only run once
    every source property the script names has been read.
    """
    kind = condition.kind
    if kind == "compare":
        return _compare(state.slots[condition.slot][1], condition.op,
                        condition.operand, condition.type)
    if kind == "check":
        return state.checks[condition.index]
    if kind == "aggregate":
        return _compare(_count_of(condition.agg, condition.group, state),
                        condition.op, condition.operand, "int")
    if kind == "all":
        return all(_evaluate_condition(i, state) for i in condition.items)
    if kind == "any":
        return any(_evaluate_condition(i, state) for i in condition.items)
    if kind == "not":
        return not _evaluate_condition(condition.item, state)
    raise RuntimeError("unknown condition kind '" + kind + "'")


def _count_of(agg, group, state):
    """!
    Counts checks in a group. A group of None means every named check.
    """
    indexes = range(len(state.checks)) if group is None else group
    count = 0
    for index in indexes:
        value = state.checks[index]
        if agg == "Passed" and value is True:
            count += 1
        elif agg == "Failed" and value is False:
            count += 1
    return count


def _compare(left, op, right, type):
    if op == "Eq":
        return left == right
    if op == "Ne":
        return left != right
    if op == "Gt":
        return left > right
    if op == "Ge":
        return left >= right
    if op == "Lt":
        return left < right
    if op == "Le":
        return left <= right
    if op == "In":
        return any(member == left for member in right)
    if op == "NotIn":
        return not any(member == left for member in right)
    if op == "StartsWith":
        return left.startswith(right)
    if op == "EndsWith":
        return left.endswith(right)
    if op == "Contains":
        return right in left
    raise RuntimeError("unknown operator '" + op + "' on type " + type)


# ---------------------------------------------------------------------
# Messages.
# ---------------------------------------------------------------------

def _missing_message(model, missing, reasons):
    count = len(missing)
    noun = ("1 source property was not available" if count == 1
            else str(count) + " source properties were not available")
    details = " ".join(
        "'" + p.name + "' (" + reason + ")."
        for p, reason in zip(missing, reasons))
    return ("Derived property '" + model.output["Name"] + "' has no value "
            "because " + noun + ". " + details + " " + USUAL_CAUSES)

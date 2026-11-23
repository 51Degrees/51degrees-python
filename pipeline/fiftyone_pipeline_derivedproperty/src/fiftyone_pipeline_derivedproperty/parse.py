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
Turns the text of a derived property script into plain Python values.
YAML and JSON are both accepted and give the same values.

This follows tools/parse.mjs of derived-properties, which reads YAML with
the YAML core schema. PyYAML follows YAML 1.1, where yes, no, on and off
are booleans and a date is a date, so the loader here keeps only the core
schema's null, boolean, integer and float forms, and every other plain
value is a string. Mapping keys are strings, as they are in JavaScript,
and a key written twice is refused.

Where the text is YAML the parser also records the line each mapping and
each sequence started on, so a validation fault can point at a line.
"""

import json
import re

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, SequenceNode

from .jsvalues import js_string


class ParseError(Exception):
    """! Raised when the text is not YAML or JSON, or is not a mapping. """

    def __init__(self, message, line=None):
        """!
        @param message: what is wrong with the text.
        @param line: the one based line, or None where it is not known.
        """
        super().__init__(message)
        self.message = message
        self.line = line


class ParseResult(object):
    """! The values read from a script, and where each one started. """

    def __init__(self, format, document, lines):
        self.format = format
        self.document = document
        # The one based line of each mapping and list, by id.
        self._lines = lines

    def line_of(self, node):
        """!
        The one based line a mapping or list in the document started on,
        or None when it is not known.
        """
        if not isinstance(node, (dict, list)):
            return None
        entry = self._lines.get(id(node))
        return None if entry is None else entry[1]


def parse(text):
    """!
    Reads script text.

    @param text: the script, as YAML or as JSON.
    @rtype: ParseResult
    """
    if not isinstance(text, str):
        raise ParseError("script text must be a string")
    if re.match(r"^\s*\{", text):
        return _parse_json(text)
    return _parse_yaml(text)


def line_of(result, node):
    """! The one based line a mapping or list started on, or None. """
    if result is None:
        return None
    return result.line_of(node)


def _parse_json(text):
    try:
        # Where a key is written twice the last one is kept, as
        # JavaScript's JSON.parse keeps it.
        document = json.loads(text)
    except ValueError as error:
        raise ParseError("the text is not valid JSON: " + str(error))
    _require_mapping(document)
    lines = {}
    _require_distinct_keys(document, lines)
    return ParseResult("json", document, lines)


class _CoreLoader(yaml.SafeLoader):
    """! A loader reading the YAML core schema, recording lines. """

    yaml_implicit_resolvers = {}

    def __init__(self, stream):
        super().__init__(stream)
        # The value of each id is held with its line so the id cannot be
        # given to another value while the document is read.
        self.lines = {}

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None, "expected a mapping", node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = js_string(self.construct_object(key_node, deep=True))
            if key in mapping:
                raise ConstructorError(
                    None, None, "duplicated mapping key",
                    key_node.start_mark)
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping

    def construct_core_map(self, node):
        data = {}
        self.lines[id(data)] = (data, node.start_mark.line + 1)
        yield data
        data.update(self.construct_mapping(node))

    def construct_core_seq(self, node):
        data = []
        self.lines[id(data)] = (data, node.start_mark.line + 1)
        yield data
        data.extend(self.construct_sequence(node))

    def construct_core_int(self, node):
        value = self.construct_scalar(node)
        if value.startswith("0o"):
            return int(value[2:], 8)
        if value.startswith("0x"):
            return int(value[2:], 16)
        return int(value, 10)


_CoreLoader.add_implicit_resolver(
    "tag:yaml.org,2002:null",
    re.compile(r"^(?:~|null|Null|NULL|)$"),
    ["~", "n", "N", ""])
_CoreLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"))
_CoreLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$"),
    list("-+0123456789"))
_CoreLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)"
               r"(?:[eE][-+]?[0-9]+)?"
               r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$"),
    list("-+0123456789."))
_CoreLoader.add_constructor(
    "tag:yaml.org,2002:map", _CoreLoader.construct_core_map)
_CoreLoader.add_constructor(
    "tag:yaml.org,2002:seq", _CoreLoader.construct_core_seq)
_CoreLoader.add_constructor(
    "tag:yaml.org,2002:int", _CoreLoader.construct_core_int)


def _parse_yaml(text):
    loader = _CoreLoader(text)
    try:
        document = loader.get_single_data()
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        line = mark.line + 1 if mark is not None else None
        reason = getattr(error, "problem", None) or str(error)
        raise ParseError("the text is not valid YAML: " + reason, line)
    finally:
        loader.dispose()
    _require_mapping(document)
    _require_distinct_keys(document, loader.lines)
    return ParseResult("yaml", document, loader.lines)


def _require_distinct_keys(node, lines):
    """!
    Every key in the format is matched without regard to case, so two
    keys in one mapping that differ only in case are one key written
    twice, and both are refused.
    """
    if isinstance(node, list):
        for item in node:
            _require_distinct_keys(item, lines)
        return
    if not isinstance(node, dict):
        return
    seen = {}
    for key in node.keys():
        lower = key.lower()
        if lower in seen:
            entry = lines.get(id(node))
            raise ParseError(
                "the keys '" + seen[lower] + "' and '" + key + "' differ "
                "only in case, and keys are matched without regard to "
                "case, so one of the two would be dropped",
                None if entry is None else entry[1])
        seen[lower] = key
        _require_distinct_keys(node[key], lines)


def _require_mapping(document):
    if document is None:
        raise ParseError("the script is empty")
    if not isinstance(document, dict):
        raise ParseError(
            "the script must be a mapping of keys to values at the top "
            "level")

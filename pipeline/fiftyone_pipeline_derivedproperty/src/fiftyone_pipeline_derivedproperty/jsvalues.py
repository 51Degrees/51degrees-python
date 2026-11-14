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
The few JavaScript rules the reference tools of derived-properties rely
on, so that this package reads, compares and prints values as they do.
JavaScript has one number type, so 8 and 8.0 are the same value and both
print as 8, and a boolean is never a number, which in Python it is.
"""

import json
import math


def is_bool(value):
    """! Whether a value is a boolean. """
    return isinstance(value, bool)


def is_number(value):
    """! Whether a value is a number, which a boolean is not. """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_whole(value):
    """! Whether a value is a whole number, as Number.isInteger says. """
    if not is_number(value):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value) and value.is_integer()


def is_string(value):
    """! Whether a value is a string. """
    return isinstance(value, str)


def is_list(value):
    """! Whether a value is a list. """
    return isinstance(value, list)


def is_mapping(value):
    """! Whether a value is a mapping. """
    return isinstance(value, dict)


def number_text(value):
    """!
    A number as JavaScript prints it, so a whole number has no decimal
    point.
    """
    if isinstance(value, int):
        return str(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    text = repr(value)
    if "e" in text:
        mantissa, exponent = text.split("e")
        sign = "-" if exponent.startswith("-") else "+"
        text = mantissa + "e" + sign + exponent.lstrip("+-").lstrip("0")
    return text


def js_string(value):
    """! A value as JavaScript's String() gives it. """
    if value is None:
        return "null"
    if is_bool(value):
        return "true" if value else "false"
    if is_number(value):
        return number_text(value)
    if is_string(value):
        return value
    if is_list(value):
        return ",".join(
            "" if item is None else js_string(item) for item in value)
    return "[object Object]"


def _plain(value):
    """! A value with every whole number held as an int. """
    if is_number(value) and isinstance(value, float) and is_whole(value):
        return int(value)
    if is_list(value):
        return [_plain(item) for item in value]
    if is_mapping(value):
        return {key: _plain(item) for key, item in value.items()}
    return value


def js_json(value, indent=None):
    """!
    A value as JavaScript's JSON.stringify() gives it, with no spaces
    unless an indent is given.
    """
    if indent is None:
        return json.dumps(_plain(value), ensure_ascii=False,
                          separators=(",", ":"))
    return json.dumps(_plain(value), ensure_ascii=False, indent=indent)

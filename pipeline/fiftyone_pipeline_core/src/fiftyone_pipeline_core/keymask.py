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

import re

# How many characters at the end of a key are shown.
VISIBLE_CHARACTERS = 4

# A licence key in a URL query string or in text that holds one, whatever the
# parameter is called (licenseKeys, licenceKey, license_keys and so on).
_LICENCE_PARAMETER = re.compile(
    r"(licen[cs]e(?:_?keys?)?=)([^&\s'\"#]*)", re.IGNORECASE)

# The separator of a list of keys, written as it is or percent encoded.
_KEY_SEPARATOR = re.compile(r"(\||%7C)", re.IGNORECASE)


def mask_licence_key(key):
    """!
    A licence key with each character hidden by an asterisk, except the last
    four. A key of four or fewer characters is hidden entirely.
    @type key: str
    @param key: The licence key
    @rtype: str
    @return: The masked key, of the same length
    """

    key = str(key)
    if len(key) <= VISIBLE_CHARACTERS:
        return "*" * len(key)
    return "*" * (len(key) - VISIBLE_CHARACTERS) + key[-VISIBLE_CHARACTERS:]


def _mask_parameter(match):
    parts = _KEY_SEPARATOR.split(match.group(2))
    masked = [mask_licence_key(part) if index % 2 == 0 else part
              for index, part in enumerate(parts)]
    return match.group(1) + "".join(masked)


def mask_licence_keys_in_text(text):
    """!
    Text, such as a URL or an error message, with every licence key in a
    licence parameter masked as :func:`mask_licence_key` does. A list of keys
    separated by a vertical bar is masked key by key.
    @type text: str
    @param text: The text that may hold a licence key
    @rtype: str
    @return: The text with the keys masked
    """

    return _LICENCE_PARAMETER.sub(_mask_parameter, str(text))

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
The callback URL the client script posts to for updated JSON. The protocol
and host usually come from the request, and the script holds the URL in a
single-quoted string, so the URL is checked before it is written into the
script. A URL that is not valid, including one whose protocol is not http or
https, is refused. In the user information, in anything after the host and
port, and in the endpoint, the characters a URL cannot hold or that could end
the string or the script are percent-encoded.

See https://github.com/51Degrees/specifications/blob/main/pipeline-specification/pipeline-elements/javascript-builder.md#callback-url
"""

import re
from collections import namedtuple

# Whether the URL can be written into the script, and the URL. That is the
# URL to write into the script when it is valid, and otherwise the URL as it
# was built, for the log.
CallbackUrl = namedtuple("CallbackUrl", ["valid", "url"])

# The largest port number.
MAX_PORT = 65535

# The most digits a port can have once its leading zeros are dropped.
MAX_PORT_DIGITS = 5

# The printable ASCII characters that are percent-encoded, besides the
# control characters, the space and everything outside ASCII.
ENCODED_CHARACTERS = frozenset(b"\"'<>\\^`{|}")

HEX_DIGITS = frozenset(b"0123456789ABCDEFabcdef")

# Text made only of the Unicode White_Space characters, which counts as a
# part that is not set. The first range is tab, line feed, vertical tab,
# form feed and carriage return.
BLANK_PATTERN = re.compile(
    r"[\t-\r \u0085\u00a0\u1680\u2000-\u200a"
    r"\u2028\u2029\u202f\u205f\u3000]*")

# The schemes the script can send its request with. It uses the URL only with
# fetch and XMLHttpRequest, which reach a server with no other scheme.
SCHEMES = ("http", "https")

# Lower-cases the ASCII letters A to Z and nothing else.
_ASCII_LOWER = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")

# Where the authority ends, which is at the first '/', '?' or '#' of the
# host.
AUTHORITY_END_PATTERN = re.compile(r"[/?#]")

# A label of a host name, being ASCII letters, digits, '-' and '_'.
LABEL_PATTERN = re.compile(r"[A-Za-z0-9_-]+")

# An IPv6 zone identifier, being unreserved characters as RFC 3986 section
# 2.3 defines them.
ZONE_PATTERN = re.compile(r"[A-Za-z0-9._~-]+")

# A port as it follows the host, being ':' and any number of digits.
PORT_PATTERN = re.compile(r":[0-9]*")

# One group of an IPv6 address.
HEX_GROUP_PATTERN = re.compile(r"[0-9A-Fa-f]{1,4}")

# An IPv4 address as RFC 3986 section 3.2.2 defines one, being four numbers
# from 0 to 255 with no leading zeros.
_DEC_OCTET = r"(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
IPV4_PATTERN = re.compile(_DEC_OCTET + r"(\." + _DEC_OCTET + r"){3}")

# A lone surrogate, which has no UTF-8 encoding, so it is written as U+FFFD,
# as a browser writes it.
SURROGATE_PATTERN = re.compile(r"[\ud800-\udfff]")


def is_blank(text):

    """!
    Whether a part of the URL is not set.

    @type text: object
    @param text: The part
    @rtype: bool
    @return: True if the part is not a string, or is empty or only
    whitespace
    """

    return (not isinstance(text, str)
            or BLANK_PATTERN.fullmatch(text) is not None)


def ascii_lower(text):

    """!
    The text with the ASCII letters A to Z in lower case and every other
    character as it is, so that no letter outside ASCII can stand in for an
    ASCII one, as str.casefold would let the long s stand in for "s".

    @type text: str
    @param text: The text
    @rtype: str
    @return: The text with A to Z in lower case
    """

    return text.translate(_ASCII_LOWER)


def is_scheme(protocol):

    """!
    Whether the protocol is http or https, ignoring the case of its ASCII
    letters only.

    @type protocol: str
    @param protocol: The protocol
    @rtype: bool
    @return: True if the protocol is http or https
    """

    return ascii_lower(protocol) in SCHEMES


def callback_url(protocol, host, endpoint):

    """!
    Build the callback URL from its parts and check it. One slash separates
    the host and the endpoint, being added when neither has one and removed
    when both do. The protocol and the host are written in lower case and
    the rest as given, apart from the percent-encoding.

    @type protocol: str
    @param protocol: The protocol, http or https in any case
    @type host: str
    @param host: The host, which can start with user information and end
    with a port, a path, a query or a fragment
    @type endpoint: str
    @param endpoint: The endpoint
    @rtype: CallbackUrl
    @return: The callback URL, or None when the protocol, host or endpoint
    is not set
    """

    if is_blank(protocol) or is_blank(host) or is_blank(endpoint):
        return None
    host_has_slash = host.endswith("/")
    endpoint_has_slash = endpoint.startswith("/")
    if not host_has_slash and not endpoint_has_slash:
        endpoint = "/" + endpoint
    elif host_has_slash and endpoint_has_slash:
        endpoint = endpoint[1:]
    built = protocol + "://" + host + endpoint
    if not is_scheme(protocol):
        return CallbackUrl(False, built)
    match = AUTHORITY_END_PATTERN.search(host)
    end = len(host) if match is None else match.start()
    authority = _checked_authority(host[:end])
    if authority is None:
        return CallbackUrl(False, built)
    return CallbackUrl(
        True,
        ascii_lower(protocol) + "://" + authority
        + _encoded(host[end:]) + _encoded(endpoint))


def _checked_authority(authority):

    """!
    The user information, host and port as they are written into the URL,
    or None when they are not valid. The user information ends at the first
    '@', so a second '@' is part of the host and refused.
    """

    user, at, host_port = authority.partition("@")
    if not at:
        return _checked_host_port(authority)
    host_port = _checked_host_port(host_port)
    if host_port is None:
        return None
    return _encoded(user) + "@" + host_port


def _checked_host_port(host_port):

    """!
    The host and optional port in lower case, or None when they are not
    valid. The host is an IPv6 address in brackets with an optional zone
    identifier, or a name of labels separated by dots with a dot allowed at
    the end. The port is ':' followed by digits up to 65535, or by nothing.
    """

    if host_port.startswith("["):
        close = host_port.find("]")
        if close == -1:
            return None
        address, separator, zone = host_port[1:close].partition("%25")
        if separator and ZONE_PATTERN.fullmatch(zone) is None:
            return None
        if not _is_ipv6(address):
            return None
        host = host_port[:close + 1]
        port = host_port[close + 1:]
    else:
        host, colon, port = host_port.partition(":")
        port = colon + port
        name = host[:-1] if host.endswith(".") else host
        for label in name.split("."):
            if LABEL_PATTERN.fullmatch(label) is None:
                return None
    if port and not _is_port(port):
        return None
    return host.lower() + port


def _is_port(text):

    """!
    Whether the text is ':' followed by digits whose value is no more than
    65535, or by nothing.
    """

    if PORT_PATTERN.fullmatch(text) is None:
        return False
    digits = text[1:].lstrip("0")
    return len(digits) <= MAX_PORT_DIGITS and (
        not digits or int(digits) <= MAX_PORT)


def _is_ipv6(text):

    """!
    Whether the text is an IPv6 address as RFC 3986 section 3.2.2 defines
    one. That is eight groups of one to four hexadecimal digits separated by
    ':', where one '::' can stand for one or more groups of zeros and the
    last two groups can be written as an IPv4 address.
    """

    gap = text.find("::")
    if gap == -1:
        return _groups(text, True) == 8
    if text.find("::", gap + 1) != -1:
        return False
    head = _groups(text[:gap], False)
    tail = _groups(text[gap + 2:], True)
    return head >= 0 and tail >= 0 and head + tail <= 7


def _groups(run, ipv4_at_end):

    """!
    The number of 16 bit groups in a run of groups separated by ':', or -1
    when the run is not valid. An empty run has none, and an IPv4 address at
    the end of the run, where one is allowed, counts as two.
    """

    if not run:
        return 0
    parts = run.split(":")
    count = 0
    for i, part in enumerate(parts):
        if HEX_GROUP_PATTERN.fullmatch(part):
            count += 1
        elif (ipv4_at_end and i == len(parts) - 1
                and IPV4_PATTERN.fullmatch(part)):
            count += 2
        else:
            return -1
    return count


def _encoded(text):

    """!
    The text with each byte of its UTF-8 encoding percent-encoded where the
    byte is a control character, a space, outside ASCII or one of
    ENCODED_CHARACTERS, and with a '%' encoded where two hexadecimal digits
    do not follow it.
    """

    data = SURROGATE_PATTERN.sub("\ufffd", text).encode("utf-8")
    out = []
    for i, b in enumerate(data):
        if b == 0x25:
            keep = (i + 2 < len(data)
                    and data[i + 1] in HEX_DIGITS
                    and data[i + 2] in HEX_DIGITS)
        else:
            keep = 0x20 < b < 0x7F and b not in ENCODED_CHARACTERS
        out.append(chr(b) if keep else "%{:02X}".format(b))
    return "".join(out)

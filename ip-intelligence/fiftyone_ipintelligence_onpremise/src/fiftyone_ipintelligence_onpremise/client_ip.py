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

import ipaddress
import re

# The prefixes the native code reads the client IP keys under, in the order
# it reads them.
PREFIXES = ("query.", "server.")

# An IPv6 address in brackets, with or without a port, and an IPv4 address
# with a port. A port is one or more ASCII digits.
BRACKETED = re.compile(r"\[([^\[\]]*)\](?::([0-9]+))?")
WITH_PORT = re.compile(r"([0-9.]+):([0-9]+)")
MAX_PORT = 65535


def client_ip_keys(keys):

    """!
    The client IP evidence keys in the order the native code reads them,
    every query key in the order given, then every server key in the
    order given.

    @type keys: list
    @param keys: the engine's evidence keys, in the data file's order
    @rtype: list
    """

    return [key for prefix in PREFIXES for key in keys
            if key.lower().startswith(prefix)]


def read_client_ip(value):

    """!
    The address a client IP value holds, or None when the whole value is
    not one address, an IPv4 address with a port, or an IPv6 address in
    brackets with or without a port. A port is dropped. An IPv4-mapped IPv6
    address is its IPv4 address. A value holding a zone index is not read.

    @rtype: ipaddress.IPv4Address or ipaddress.IPv6Address or None
    """

    text = str(value)
    # ipaddress reads a zone index, such as fe80::1%eth0, and the whole
    # value must be refused rather than read with the zone dropped. The
    # percent sign only ever starts a zone index here, in the plain and the
    # %25 encoded form alike.
    if "%" in text:
        return None
    version = None
    port = None
    match = BRACKETED.fullmatch(text)
    if match:
        text, port, version = match.group(1), match.group(2), 6
    else:
        match = WITH_PORT.fullmatch(text)
        if match:
            text, port, version = match.group(1), match.group(2), 4
    if port is not None and int(port) > MAX_PORT:
        return None
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return None
    if version is not None and address.version != version:
        return None
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address


def readable_client_ips(evidence, keys):

    """!
    Each client IP value that is read, as (key, address), in the order the
    native code reads the keys. A key is matched with the evidence in any
    letter case, and keeps the spelling the engine gives it.

    @type evidence: dict
    @param evidence: every evidence key and value
    @type keys: list
    @param keys: the engine's evidence keys, in the data file's order
    @rtype: list
    """

    supplied = {}
    for key, value in evidence.items():
        supplied.setdefault(str(key).lower(), value)
    found = []
    for key in client_ip_keys(keys):
        value = supplied.get(key.lower())
        if value is None:
            continue
        address = read_client_ip(value)
        if address is not None:
            found.append((key, address))
    return found


def client_ips(evidence, keys):

    """!
    The address the engine reports in Ip or IpV6, being the first client IP
    value that is read, which is the one the native code looks up, as the
    Choosing the IP address and Reading the client IP value sections of the
    specification say. A value that is not read does not hide a value under
    a key that comes later.

    @type evidence: dict
    @param evidence: every evidence key and value
    @type keys: list
    @param keys: the engine's evidence keys, in the data file's order
    @rtype: tuple
    @returns: (ipv4 or None, ipv6 or None), with at most one set
    """

    found = readable_client_ips(evidence, keys)
    if not found:
        return (None, None)
    address = found[0][1]
    if address.version == 4:
        return (str(address), None)
    return (None, str(address))

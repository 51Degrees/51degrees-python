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

# The evidence keys read first, in order.
CLIENT_IP_KEYS = ("query.client-ip", "server.client-ip")


def client_ips(evidence, keys=None):

    """!
    The IPv4 and IPv6 addresses the engine reports in Ip and IpV6, read from
    the evidence, query.client-ip first, then server.client-ip, then any
    other value that is an address as given. An IPv4-mapped IPv6 address,
    such as ::ffff:8.8.8.8, is its IPv4 address and is reported as Ip, as
    the native code looks it up. A value holding a zone index, such as
    fe80::1%eth0, is not read at all.

    @type evidence: dict
    @param evidence: every evidence key and value
    @type keys: list
    @param keys: the engine's client IP evidence keys, not yet used
    @rtype: tuple
    @returns: (ipv4 or None, ipv6 or None)
    """

    ordered = []
    for key in CLIENT_IP_KEYS:
        if key in evidence:
            ordered.append(evidence[key])
    for key, value in evidence.items():
        if value not in ordered:
            ordered.append(value)

    ipv4 = None
    ipv6 = None
    for value in ordered:
        text = str(value)
        # ipaddress reads a zone index, such as fe80::1%eth0, and the
        # engine must refuse the whole value rather than read the address
        # and drop the zone. The percent sign only ever starts a zone
        # index here, in the plain and the %25 encoded form alike.
        if "%" in text:
            continue
        try:
            parsed = ipaddress.ip_address(text)
        except ValueError:
            continue
        if parsed.version == 6 and parsed.ipv4_mapped is not None:
            parsed = parsed.ipv4_mapped
        if parsed.version == 4 and ipv4 is None:
            ipv4 = str(parsed)
        elif parsed.version == 6 and ipv6 is None:
            ipv6 = str(parsed)

    return (ipv4, ipv6)

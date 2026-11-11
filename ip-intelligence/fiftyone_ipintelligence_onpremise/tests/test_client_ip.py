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

"""The client addresses the engine reports in Ip and IpV6, as the Address
forms section of the IP Intelligence on-premise specification says."""

import unittest

from fiftyone_ipintelligence_onpremise.client_ip import client_ips


class ClientIpTests(unittest.TestCase):

    def test_an_ipv4_mapped_address_is_its_ipv4_address(self):
        for text in ("::ffff:8.8.8.8", "::ffff:808:808",
                     "0:0:0:0:0:ffff:808:808"):
            self.assertEqual(
                ("8.8.8.8", None),
                client_ips({"query.client-ip": text}), text)

    def test_ipv4_compatible_and_embedded_addresses_stay_ipv6(self):
        self.assertEqual(
            (None, "::808:808"),
            client_ips({"query.client-ip": "::8.8.8.8"}))
        self.assertEqual(
            (None, "64:ff9b::808:808"),
            client_ips({"query.client-ip": "64:ff9b::8.8.8.8"}))

    def test_an_address_with_spaces_is_not_read(self):
        self.assertEqual(
            (None, None), client_ips({"query.client-ip": " 8.8.8.8 "}))

    def test_a_zone_index_is_not_read(self):
        for text in ("fe80::1%eth0", "fe80::1%1", "[fe80::1%eth0]",
                     "[fe80::1%25eth0]", "::ffff:8.8.8.8%1",
                     "::ffff:8.8.8.8%eth0"):
            self.assertEqual(
                (None, None),
                client_ips({"query.client-ip": text}), text)

    def test_a_zone_index_does_not_hide_a_later_value(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"query.client-ip": "fe80::1%eth0",
                        "server.client-ip": "1.2.3.4"}))

    def test_the_client_ip_query_comes_first(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"server.client-ip": "5.6.7.8",
                        "query.client-ip": "1.2.3.4"}))


if __name__ == "__main__":
    unittest.main()

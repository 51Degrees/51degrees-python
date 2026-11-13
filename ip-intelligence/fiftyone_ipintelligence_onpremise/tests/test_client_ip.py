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

"""The client addresses the engine reports in Ip and IpV6, as the Choosing
the IP address, Reading the client IP value and Address forms sections of
the IP Intelligence on-premise specification say."""

import unittest

from fiftyone_ipintelligence_onpremise.client_ip import client_ips


# The client IP keys as an engine might list them, in the data file's order
# with both prefixes mixed together.
KEYS = ["server.true-client-ip-51d", "query.true-client-ip-51d",
        "server.client-ip", "query.client-ip"]


class ClientIpTests(unittest.TestCase):

    def test_an_ipv4_mapped_address_is_its_ipv4_address(self):
        for text in ("::ffff:8.8.8.8", "::ffff:808:808",
                     "0:0:0:0:0:ffff:808:808"):
            self.assertEqual(
                ("8.8.8.8", None),
                client_ips({"query.client-ip": text}, KEYS), text)

    def test_ipv4_compatible_and_embedded_addresses_stay_ipv6(self):
        self.assertEqual(
            (None, "::808:808"),
            client_ips({"query.client-ip": "::8.8.8.8"}, KEYS))
        self.assertEqual(
            (None, "64:ff9b::808:808"),
            client_ips({"query.client-ip": "64:ff9b::8.8.8.8"}, KEYS))

    def test_an_address_with_spaces_is_not_read(self):
        self.assertEqual(
            (None, None), client_ips({"query.client-ip": " 8.8.8.8 "}, KEYS))

    def test_a_zone_index_is_not_read(self):
        for text in ("fe80::1%eth0", "fe80::1%1", "[fe80::1%eth0]",
                     "[fe80::1%25eth0]", "::ffff:8.8.8.8%1",
                     "::ffff:8.8.8.8%eth0"):
            self.assertEqual(
                (None, None),
                client_ips({"query.client-ip": text}, KEYS), text)

    def test_a_zone_index_does_not_hide_a_later_value(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"query.client-ip": "fe80::1%eth0",
                        "server.client-ip": "1.2.3.4"}, KEYS))

    def test_the_client_ip_query_comes_first(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"server.client-ip": "5.6.7.8",
                        "query.client-ip": "1.2.3.4"}, KEYS))

    def test_a_leading_zero_is_not_read(self):
        # The rule is kept by ipaddress, which refuses a leading zero, so
        # this catches a Python that reads one.
        for text in ("01.2.3.4", "1.02.3.4", "1.2.3.04", "00.0.0.0",
                     "::ffff:01.2.3.4"):
            self.assertEqual(
                (None, None),
                client_ips({"query.client-ip": text}, KEYS), text)
        self.assertEqual(
            ("0.0.0.0", None), client_ips({"query.client-ip": "0.0.0.0"}, KEYS))


class ClientIpChoiceTests(unittest.TestCase):

    def test_only_the_client_ip_keys_are_read(self):
        self.assertEqual(
            (None, None),
            client_ips({"header.x-real-ip": "1.2.3.4"}, KEYS))

    def test_the_query_keys_come_first_in_the_data_files_order(self):
        self.assertEqual(
            ("9.9.9.9", None),
            client_ips({"server.true-client-ip-51d": "5.6.7.8",
                        "query.client-ip": "1.2.3.4",
                        "query.true-client-ip-51d": "9.9.9.9"}, KEYS))

    def test_the_server_keys_are_read_when_no_query_key_has_an_address(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"server.client-ip": "5.6.7.8",
                        "server.true-client-ip-51d": "1.2.3.4",
                        "query.client-ip": "unknown"}, KEYS))

    def test_the_keys_match_in_any_letter_case(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"Server.Client-IP": "5.6.7.8",
                        "QUERY.CLIENT-IP": "1.2.3.4"}, KEYS))

    def test_only_the_address_looked_up_is_reported(self):
        self.assertEqual(
            ("1.2.3.4", None),
            client_ips({"query.client-ip": "1.2.3.4",
                        "server.client-ip": "2001:db8::1"}, KEYS))

    def test_a_port_and_brackets_are_read_and_the_port_dropped(self):
        for text, expected in (
                ("203.0.113.1:8080", ("203.0.113.1", None)),
                ("203.0.113.1:0", ("203.0.113.1", None)),
                ("203.0.113.1:65535", ("203.0.113.1", None)),
                ("[2001:db8::1]", (None, "2001:db8::1")),
                ("[2001:db8::1]:8080", (None, "2001:db8::1")),
                ("[::ffff:8.8.8.8]:80", ("8.8.8.8", None))):
            self.assertEqual(
                expected, client_ips({"query.client-ip": text}, KEYS), text)

    def test_an_ipv6_address_without_brackets_has_no_port(self):
        self.assertEqual(
            (None, "2001:db8::1:80"),
            client_ips({"query.client-ip": "2001:db8::1:80"}, KEYS))

    def test_the_values_the_specification_does_not_read(self):
        for text in ("203.0.113.0/24", "203.0.113.1 x",
                     "203.0.113.1, 198.51.100.7", "203.0.113.1	",
                     "[203.0.113.1]", "[2001:db8::1", "2001:db8::1]:80",
                     "203.0.113.1:", "203.0.113.1:65536",
                     "203.0.113.1:８０", "256.0.113.1",
                     "203.0.113", "2001:db8::1::2", "2001:db8:1:2:3:4:5:6:7",
                     "2001:db8::12345", "unknown", "", "[fe80::1%eth0]:80"):
            self.assertEqual(
                (None, None), client_ips({"query.client-ip": text}, KEYS),
                text)


if __name__ == "__main__":
    unittest.main()

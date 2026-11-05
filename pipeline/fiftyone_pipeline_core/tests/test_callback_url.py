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

"""
Checks the callback URL against the cases every implementation of the
JavaScript builder shares, in the same order, so that each one refuses and
writes the same URLs.
"""

import unittest

from parameterized import parameterized

from fiftyone_pipeline_core.callback_url import CallbackUrl, callback_url

ENDPOINT = "/51dpipeline/json"


def _url(protocol, host):
    return callback_url(protocol, host, ENDPOINT)


def _valid(text):
    return CallbackUrl(True, text)


class CallbackUrlTests(unittest.TestCase):

    def test_adds_a_single_slash(self):
        self.assertEqual(
            _valid("https://example.com/51dpipeline/json"),
            callback_url("https", "example.com", "51dpipeline/json"))

    def test_keeps_a_single_slash_on_the_endpoint(self):
        self.assertEqual(
            _valid("https://example.com/51dpipeline/json"),
            callback_url("https", "example.com", "/51dpipeline/json"))

    def test_collapses_a_double_slash(self):
        self.assertEqual(
            _valid("http://example.com/json"),
            callback_url("http", "example.com/", "/json"))

    def test_missing_when_a_part_is_empty(self):
        self.assertIsNone(callback_url("https", "", "/json"))
        self.assertIsNone(callback_url("", "example.com", "/json"))
        self.assertIsNone(callback_url("https", "example.com", ""))
        self.assertIsNone(callback_url("https", "  ", "/json"))

    @parameterized.expand([
        ("EXAMPLE.com", "https://example.com/51dpipeline/json"),
        ("example.com:8080", "https://example.com:8080/51dpipeline/json"),
        ("example.com:", "https://example.com:/51dpipeline/json"),
        ("example.com:65535", "https://example.com:65535/51dpipeline/json"),
        ("a_b.com", "https://a_b.com/51dpipeline/json"),
        ("-ab.com", "https://-ab.com/51dpipeline/json"),
        ("127.0.0.1:80", "https://127.0.0.1:80/51dpipeline/json"),
        ("[::1]", "https://[::1]/51dpipeline/json"),
        ("[::1]:8080", "https://[::1]:8080/51dpipeline/json"),
        ("[fe80::1%25eth0]", "https://[fe80::1%25eth0]/51dpipeline/json"),
        ("user:pw@example.com",
         "https://user:pw@example.com/51dpipeline/json"),
        ("u x@example.com", "https://u%20x@example.com/51dpipeline/json"),
        ("u\tx@example.com", "https://u%09x@example.com/51dpipeline/json"),
        ("example.com.", "https://example.com./51dpipeline/json"),
        ("example.com/path", "https://example.com/path/51dpipeline/json"),
        ("example.com?x", "https://example.com?x/51dpipeline/json"),
        ("example.com/a b", "https://example.com/a%20b/51dpipeline/json"),
        ("example.com/a%zzb",
         "https://example.com/a%25zzb/51dpipeline/json"),
        ("example.com/a%41b", "https://example.com/a%41b/51dpipeline/json"),
        ("example.com/\u00fc",
         "https://example.com/%C3%BC/51dpipeline/json"),
        ("example.com/a\nb", "https://example.com/a%0Ab/51dpipeline/json"),
        ("example.com/a\u2028b",
         "https://example.com/a%E2%80%A8b/51dpipeline/json"),
    ])
    def test_accepts_the_host(self, host, expected):
        self.assertEqual(_valid(expected), _url("https", host))

    @parameterized.expand([
        ("example.com:65536",),
        ("example.com:99999",),
        ("example.com:abc",),
        ("exa mple.com",),
        ("example.com');alert(1);//",),
        ("a\"b.com",),
        ("a'b.com",),
        ("a<b.com",),
        ("::1",),
        ("[::1",),
        ("[v1.x]",),
        ("[1.2.3.4]",),
        ("a@b@example.com",),
        ("a..b.com",),
        ("%41.com",),
        ("a\\b.com",),
        ("a`b.com",),
        ("a{b}.com",),
        ("a|b.com",),
        ("a^b.com",),
        ("a(b).com",),
        ("a;b.com",),
        ("a,b.com",),
        ("a!b.com",),
        ("a*b.com",),
        ("a+b.com",),
        ("a=b.com",),
        ("a$b.com",),
        ("a&b.com",),
        ("a~b.com",),
        ("a\tb.com",),
        ("a\nb.com",),
        (" example.com",),
        ("example.com ",),
        ("example.com:8080');alert(1);//",),
    ])
    def test_refuses_the_host(self, host):
        self.assertFalse(_url("https", host).valid, repr(host))

    @parameterized.expand([
        ("[fe80::1%25]",),
        ("[fe80::1%25'+alert(1)+']",),
        ("[fe80::1%eth0]",),
        ("[fe80::1%25eth%0]",),
        ("[::1]x",),
        ("[::1]80",),
        ("[::1]:80x",),
        ("[::1]]",),
    ])
    def test_refuses_the_zone_or_the_text_after_the_bracket(self, host):
        """Inside the brackets only an IPv6 address, optionally followed by
        '%25' and a zone of unreserved characters, and after them only a
        port. The zone check is what keeps a quote out of the script for a
        bracketed host."""

        self.assertFalse(_url("https", host).valid, repr(host))

    def test_accepts_a_zone_followed_by_a_port(self):
        self.assertEqual(
            _valid("https://[fe80::1%25eth0]:8080/51dpipeline/json"),
            _url("https", "[fe80::1%25eth0]:8080"))

    def test_checks_the_port_by_its_value(self):
        """A port goes by its value, so leading zeros are allowed, and a
        port too long to read is refused rather than read as small enough."""

        self.assertEqual(
            _valid("https://example.com:00080/51dpipeline/json"),
            _url("https", "example.com:00080"))
        self.assertEqual(
            _valid("https://example.com:0065535/51dpipeline/json"),
            _url("https", "example.com:0065535"))
        for host in [
                "example.com:0065536",
                "example.com:123456",
                "example.com:4294967296",
                "example.com:99999999999999999999"]:
            self.assertFalse(_url("https", host).valid, host)

    def test_encodes_the_characters_rule_8_lists(self):
        """Each character rule 8 lists, in the user information, after the
        host and in the endpoint, and a '%' without two hexadecimal digits
        after it, even at the end."""

        self.assertEqual(
            _valid("https://u%22%5E%60%7B%7C%7D@example.com/%22%5E%60%7B%7C%7D"
                   "/j%22%5E%60%7B%7C%7D"),
            callback_url(
                "https", 'u"^`{|}@example.com/"^`{|}', '/j"^`{|}'))
        self.assertEqual(
            _valid("https://example.com/a%25/51dpipeline/json"),
            _url("https", "example.com/a%"))
        self.assertEqual(
            _valid("https://example.com/a%254/51dpipeline/json"),
            _url("https", "example.com/a%4"))
        self.assertEqual(
            _valid("https://example.com/a%41/51dpipeline/json"),
            _url("https", "example.com/a%41"))
        self.assertEqual(
            _valid("https://example.com/json%25"),
            callback_url("https", "example.com", "/json%"))

    def test_the_invalid_url_is_the_one_built(self):
        self.assertEqual(
            CallbackUrl(False, "https://exa mple.com/51dpipeline/json"),
            _url("https", "exa mple.com"))

    def test_checks_the_scheme(self):
        """Only http and https, ignoring the case of ASCII letters only, so
        a letter outside ASCII that a case-insensitive comparison can match
        to an ASCII one, such as the long s, is refused."""

        for protocol in ["https", "http", "HtTp"]:
            self.assertTrue(_url(protocol, "example.com").valid, protocol)
        self.assertEqual(
            _valid("https://example.com/51dpipeline/json"),
            _url("HTTPS", "example.com"))
        for protocol in [
                "ftp", "h+t-p.s", "ws", "javascript", "httpx", "https ",
                "1http", "h t", "x');alert(1);//", "a://b", "http\u017f",
                "HTTP\u017f"]:
            self.assertFalse(
                _url(protocol, "example.com").valid, repr(protocol))

    @parameterized.expand([
        ("example.com/');alert(1);//",),
        ("example.com?');alert(1);//",),
        ("example.com#');alert(1);//",),
        ("u'x@example.com",),
        ("u\\x@example.com",),
        ("example.com/a\\b",),
        ("example.com/</script>",),
    ])
    def test_nothing_given_can_end_the_string(self, host):
        """A quote, a backslash or a line break never reaches the script,
        wherever in the URL it was given."""

        result = _url("https", host)
        self.assertTrue(result.valid, repr(host))
        for c in "'\"\\<>\n\r\u2028\u2029":
            self.assertNotIn(c, result.url, repr(host))

    def test_the_endpoint_is_encoded(self):
        self.assertEqual(
            _valid("https://example.com/json%27x"),
            callback_url("https", "example.com", "/json'x"))

    @parameterized.expand([
        ("b\u00fccher.de",),
        ("a\u00a0b.com",),
        ("a\u200bb.com",),
        ("a\u2028b.com",),
    ])
    def test_refuses_the_host_outside_ascii(self, host):
        """A host must be ASCII, so an internationalized name is given as
        A-labels, and anything else outside ASCII is refused."""

        self.assertFalse(_url("https", host).valid, repr(host))

    def test_writes_a_lone_surrogate_as_the_replacement_character(self):
        """Not one of the shared cases, because only some languages' strings
        can hold a lone surrogate. It has no UTF-8 encoding, so it is written
        as U+FFFD, as a browser writes it."""

        self.assertEqual(
            _valid("https://example.com/%EF%BF%BD/51dpipeline/json"),
            _url("https", "example.com/\ud800"))


if __name__ == "__main__":
    unittest.main()

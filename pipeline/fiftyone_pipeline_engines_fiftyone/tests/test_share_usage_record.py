
"""
How the usage sharing element writes an Evidence value that was changed, as
the Processing section of the usage sharing element specification says, with
the invalid character and length rules of specifications pull request 122.
"""

import unittest

from fiftyone_pipeline_engines_fiftyone.share_usage import (
    SHARE_USAGE_MAX_EVIDENCE_LENGTH, ShareUsage, ShareUsageData)

BS = chr(92)


class ShareUsageRecordTests(unittest.TestCase):

    def record(self, value, key="header.user-agent"):
        element = ShareUsage(requested_package_size=1000)
        self.addCleanup(element.close)
        element.constant_xml = "<Version>test</Version>"
        data = ShareUsageData()
        data.session_id = "session"
        data.sequence = 1
        data.try_add(key, value)
        element.add_to_share_usage(data)
        return element.share_data[0]

    def test_limit_is_ten_thousand(self):
        self.assertEqual(10000, SHARE_USAGE_MAX_EVIDENCE_LENGTH)

    def test_unchanged_value_has_no_attributes(self):
        xml = self.record("Mozilla/5.0")
        self.assertIn('<header Name="user-agent">Mozilla/5.0</header>', xml)

    def test_invalid_character_is_written_as_hex_and_marked_escaped(self):
        xml = self.record("a" + chr(0x1f) + "b")
        self.assertIn(
            '<header Name="user-agent" escaped="true">a' + BS + 'x001fb</header>',
            xml)

    def test_other_invalid_characters(self):
        for code, text in ((0x0, "0000"), (0x8, "0008"), (0xb, "000b"),
                           (0xc, "000c"), (0xe, "000e"), (0xd800, "d800"),
                           (0xdfff, "dfff"), (0xfffe, "fffe"),
                           (0xffff, "ffff")):
            xml = self.record("x" + chr(code) + "y")
            self.assertIn("x" + BS + "x" + text + "y", xml, hex(code))
            self.assertIn(' escaped="true"', xml, hex(code))

    def test_characters_xml_allows_are_kept(self):
        value = "t" + chr(9) + chr(10) + chr(13) + chr(0x18c) + chr(0xfffd)
        xml = self.record(value)
        self.assertIn(">" + value + "<", xml)
        self.assertNotIn("escaped", xml)

    def test_markup_characters_are_still_entities(self):
        xml = self.record("a&b<c>d\"e'")
        self.assertIn(">a&amp;b&lt;c&gt;d&quot;e&apos;<", xml)
        self.assertNotIn("escaped", xml)

    def test_value_of_the_limit_is_not_truncated(self):
        xml = self.record("a" * 10000)
        self.assertIn(">" + "a" * 10000 + "<", xml)
        self.assertNotIn("truncated", xml)

    def test_longer_value_is_cut_and_marked_truncated(self):
        xml = self.record("a" * 10001)
        self.assertIn(
            ' truncated="true">' + "a" * 10000 + "</header>", xml)

    def test_length_is_counted_before_markup_characters_are_written(self):
        xml = self.record("&" * 10000)
        self.assertNotIn("truncated", xml)

    def test_character_outside_the_basic_plane_is_never_split(self):
        emoji = chr(0x1f600)
        xml = self.record("a" * 9999 + emoji + "tail")
        self.assertIn(
            ' truncated="true">' + "a" * 9999 + emoji + "</header>", xml)
        xml = self.record("a" * 9998 + emoji + emoji + "z")
        self.assertIn(
            ' truncated="true">' + "a" * 9998 + emoji + emoji + "</header>",
            xml)
        self.assertNotIn("escaped", xml)

    def test_invalid_character_in_a_long_value_sets_both(self):
        xml = self.record(chr(1) + "a" * 10000)
        self.assertIn(' escaped="true"', xml)
        self.assertIn(' truncated="true"', xml)

    def test_changed_value_is_written_without_cdata_or_bad_schema(self):
        xml = self.record("a" + chr(1) + "b")
        self.assertNotIn("CDATA", xml)
        self.assertNotIn("BadSchema", xml)
        self.assertNotIn("replaced", xml)


if __name__ == "__main__":
    unittest.main()

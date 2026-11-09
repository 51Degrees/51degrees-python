
"""
How the usage sharing element writes an Evidence value that was changed, as
the Processing section of the usage sharing element specification says.
"""

import unittest

from fiftyone_pipeline_engines_fiftyone.share_usage import (
    SHARE_USAGE_MAX_EVIDENCE_LENGTH, ShareUsage, ShareUsageData)


class ShareUsageRecordTests(unittest.TestCase):

    def record(self, key, value):
        element = ShareUsage(requested_package_size=1000)
        self.addCleanup(element.close)
        element.constant_xml = "<Version>test</Version>"
        data = ShareUsageData()
        data.session_id = "session"
        data.sequence = 1
        data.try_add(key, value)
        element.add_to_share_usage(data)
        return element.share_data[0]

    def testUnchangedValueHasNoAttributes(self):
        xml = self.record("header.user-agent", "Mozilla/5.0")
        self.assertIn('<header Name="user-agent">Mozilla/5.0</header>', xml)

    def testInvalidCharacterIsMarkedEscaped(self):
        xml = self.record("header.user-agent", "a\x01b")
        self.assertIn(' escaped="true"', xml)
        self.assertNotIn("replaced", xml)

    def testLongValueIsMarkedTruncated(self):
        xml = self.record(
            "header.user-agent", "a" * (SHARE_USAGE_MAX_EVIDENCE_LENGTH + 1))
        self.assertIn(' truncated="true"', xml)
        self.assertNotIn("escaped", xml)

    def testChangedValueIsWrittenWithoutCdataOrBadSchema(self):
        xml = self.record("header.user-agent", "a\x01b")
        self.assertNotIn("CDATA", xml)
        self.assertNotIn("BadSchema", xml)


if __name__ == "__main__":
    unittest.main()

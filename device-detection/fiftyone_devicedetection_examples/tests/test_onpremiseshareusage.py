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
Runs the usage sharing example as a person runs it, on the free evidence
file, with requests.post replaced so that nothing is sent, and checks what
would have been sent.
"""

import gzip
import inspect
import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

from fiftyone_devicedetection_examples.onpremise import shareusage

# Where usage data goes when no endpoint is given, as in the example.
DEFAULT_ENDPOINT = inspect.signature(
    ShareUsage.__init__).parameters["endpoint"].default

# The element the example's usage-from evidence becomes in each entry.
USAGE_FROM = (
    f'<header Name="usage-from">{shareusage.USAGE_FROM_VALUE}</header>')

# The start of each entry, one for each record shared.
ENTRY = "<Device>"


class ShareUsageExampleTests(unittest.TestCase):

    def test_shares_every_record_it_processes(self):
        messages = []

        def post(url, headers=None, data=None, **options):
            messages.append({
                "url": url,
                "headers": headers or {},
                "body": gzip.decompress(data).decode("utf-8"),
                "options": options,
            })
            return mock.Mock(status_code=200, text="")

        printed = io.StringIO()
        with mock.patch("requests.post", side_effect=post), \
                redirect_stdout(printed):
            shareusage.main([])

        output = printed.getvalue()
        records = shareusage.RECORDS_TO_PROCESS
        self.assertIn(f"Finished processing {records} records", output)
        self.assertIn("Done!", output)
        self.assertTrue(messages, "Nothing would have been sent")

        for message in messages:
            self.assertEqual(DEFAULT_ENDPOINT, message["url"])
            self.assertEqual(
                "gzip", message["headers"].get("Content-Encoding"))
            self.assertIsNot(False, message["options"].get("verify", True))
            # A message holds at most twice the requested package size.
            self.assertLessEqual(
                message["body"].count(ENTRY),
                2 * shareusage.REQUESTED_PACKAGE_SIZE)

        sent = "".join(message["body"] for message in messages)
        self.assertEqual(records, sent.count(ENTRY))
        self.assertEqual(records, sent.count(USAGE_FROM))
        self.assertEqual(records, sent.count("<ClientIP>"))


if __name__ == "__main__":
    unittest.main()

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
Requests the page of the on-premise User-Agent Client Hints web example, with
the headers Chrome sends on its first visit. The example finds its data file
itself, as it does in a fresh clone, so it uses the free Lite file.

The example's configuration shares usage, and usage sharing sends what is
queued when the pipeline closes, so requests.post is replaced for as long as
the pipeline is open and nothing is sent.
"""

import re
import unittest
from unittest import mock

from fiftyone_pipeline_core.logger import Logger

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise.useragentclienthints_web.app \
    import UserAgentClientHintsWeb

# The headers Chrome sends on its first request to a site, before the site
# asks for more client hints.
CHROME_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Sec-CH-UA": (
        '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'),
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

# The start of the message the page shows on the Lite file, about what the
# paid data file adds and where to ask for it.
PAID_DATA_FILE_MESSAGE = "The paid data file adds"


def used_row(key):
    """A row of the page's evidence table for evidence that was used."""
    return re.compile(
        r'<tr class="c-eg-table__row c-eg-table__row--used">\s*'
        r'<td class="c-eg-table__cell c-eg-table__cell--key">'
        + re.escape(key) + "</td>")


def result(page, label):
    """The value the page's results table shows beside the label."""
    found = re.search(
        re.escape(label) + r'</td><td class="c-eg-table__cell">(.*?)</td>',
        page)
    return found.group(1) if found else None


class OnPremiseUserAgentClientHintsWebTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_patch = mock.patch(
            "requests.post",
            return_value=mock.Mock(status_code=200, text=""))
        cls.post_patch.start()
        try:
            config = UserAgentClientHintsWeb.build_config()
            UserAgentClientHintsWeb().build(config, Logger(min_level="error"))
        except BaseException:
            cls.post_patch.stop()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            UserAgentClientHintsWeb.pipeline.close()
        finally:
            cls.post_patch.stop()
        super().tearDownClass()

    def setUp(self):
        self.client = UserAgentClientHintsWeb.app.test_client()

    def get_page(self):
        response = self.client.get("/", headers=CHROME_HEADERS)
        page = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code, page)
        return page

    def test_page_shows_the_evidence_used_and_the_browser(self):
        page = self.get_page()

        self.assertRegex(page, used_row("header.user-agent"))
        self.assertIn("header.sec-ch-ua", page)
        self.assertIn("Chrome", result(page, "Browser Name:") or "", page)

    def test_page_offers_the_enterprise_data_file(self):
        page = self.get_page()

        self.assertEqual(
            ExampleUtils.NEEDS_ENTERPRISE, result(page, "Hardware Vendor:"),
            page)
        self.assertIn(PAID_DATA_FILE_MESSAGE, page)


if __name__ == "__main__":
    unittest.main()

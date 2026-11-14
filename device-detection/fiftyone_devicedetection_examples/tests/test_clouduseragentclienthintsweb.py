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
Requests the page of the cloud User-Agent Client Hints web example, with the
headers Chrome sends on its first visit, and checks the page shows the
evidence the cloud service used and the detection results.
"""

import re
import unittest

from fiftyone_pipeline_core.logger import Logger

from fiftyone_devicedetection_examples.cloud.useragentclienthints_web.app \
    import UserAgentClientHintsWeb

from .live_cloud import find_resource_key, no_resource_key

NO_KEY = no_resource_key(
    "the device product", "device detection properties such as BrowserName")

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


def used_row(key):
    """A row of the page's evidence table for evidence that was used."""
    return re.compile(
        r'<tr class="c-eg-table__row c-eg-table__row--used">\s*'
        r'<td class="c-eg-table__cell c-eg-table__cell--key">'
        + re.escape(key) + "</td>")


class CloudUserAgentClientHintsWebTests(unittest.TestCase):

    resource_key = find_resource_key()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.resource_key:
            UserAgentClientHintsWeb().build(
                cls.resource_key, Logger(min_level="error"))

    @classmethod
    def tearDownClass(cls):
        if cls.resource_key:
            UserAgentClientHintsWeb.pipeline.close()
        super().tearDownClass()

    def setUp(self):
        if not self.resource_key:
            self.fail(NO_KEY)
        self.client = UserAgentClientHintsWeb.app.test_client()

    def test_page_shows_the_evidence_used_and_the_results(self):
        response = self.client.get("/", headers=CHROME_HEADERS)
        page = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, page)
        self.assertRegex(page, used_row("header.user-agent"))
        self.assertIn("header.sec-ch-ua", page)
        self.assertIn("Browser Name:", page)
        self.assertNotIn("Traceback", page)


if __name__ == "__main__":
    unittest.main()

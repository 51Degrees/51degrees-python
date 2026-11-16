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

import re
import unittest

import pytest

from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_examples.cloud.gettingstarted_web.app import GettingStartedWeb

from .live_cloud import find_resource_key, no_resource_key

pytestmark = pytest.mark.live

NO_KEY = no_resource_key(
    "the device product", "device detection properties such as HardwareName")

class CloudGettingStartedWebTests(unittest.TestCase):
    # The test client sends no User-Agent of its own, so supply one that detection can
    # resolve to a hardware profile.
    CHROME_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # The pipeline is built when the tests run rather than when they are
    # collected, because building it with no resource key raises, and the
    # tests are collected whether or not they are run.
    resource_key = find_resource_key()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.resource_key:
            GettingStartedWeb().build(cls.resource_key, Logger())

    @classmethod
    def tearDownClass(cls):
        if cls.resource_key:
            GettingStartedWeb.pipeline.close()
        super().tearDownClass()

    def setUp(self):
        if not self.resource_key:
            self.fail(NO_KEY)
        self.client = GettingStartedWeb.app.test_client()

    def test_cloud_getting_started_web(self):
        response = self.client.get('/')
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Find out more", response.data)

    # The device id used to appear on the page only by accident, inside the JSON of the
    # inlined client-side script. Now that the script is served separately, check that the
    # page renders a real one of its own, and that detection actually found a profile
    # rather than returning the all-zero id.
    def test_cloud_getting_started_web_device_id(self):
        response = self.client.get('/', headers={"User-Agent": self.CHROME_USER_AGENT})
        self.assertEqual(200, response.status_code)
        device_ids = re.findall(r"\d+-\d+-\d+-\d+", response.get_data(as_text=True))
        self.assertTrue(device_ids, "No device id was rendered on the page")
        self.assertNotIn("0-0-0-0", device_ids)

    # The page references the client-side script by the '/51Degrees.core.js' name used
    # by the web integrations in the other Pipeline APIs, so check that the route
    # returns the bundle rather than, for example, falling through to the page.
    def test_cloud_getting_started_web_core_js(self):
        response = self.client.get('/51Degrees.core.js')
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/x-javascript", response.headers["Content-Type"])
        self.assertIn(b"fiftyoneDegreesManager", response.data)

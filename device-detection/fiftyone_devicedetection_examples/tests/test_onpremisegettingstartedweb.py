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

import flask_unittest
import os
import re
import tempfile
import unittest
from unittest import mock
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.onpremise.gettingstarted_web.app import GettingStartedWeb

class OnPremiseGettingStartedWebTests(flask_unittest.ClientTestCase):
    # Assign the `Flask` app object
    #data_file = ExampleUtils.find_file("51Degrees-LiteV4.1.hash")

    user_agents_file = ExampleUtils.find_file("20000 User Agents.csv")
    logger = Logger()
    config = GettingStartedWeb.build_config()
    app = GettingStartedWeb().build(config, logger).app

    def test_onpremise_getting_started_web(self, client):
        response = client.get('/')
        self.assertEqual(200, response.status_code)

    # The page references the client-side script by the '/51Degrees.core.js' name used
    # by the web integrations in the other Pipeline APIs, so check that the route
    # returns the bundle rather than, for example, falling through to the page.
    def test_onpremise_getting_started_web_core_js(self, client):
        response = client.get('/51Degrees.core.js')
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/x-javascript", response.headers["Content-Type"])
        self.assertIn(b"fiftyoneDegreesManager", response.data)

    # The script takes its sequence number from the SequenceElement. Without that
    # element in config.json the script is rendered as 'var sequence=;', which
    # does not parse, so the browser never defines 'fod'.
    def test_onpremise_getting_started_web_core_js_has_sequence(self, client):
        response = client.get('/51Degrees.core.js')
        self.assertIsNone(
            re.search(rb"sequence\s*=\s*;", response.data),
            "the script has no sequence number, so it will not parse")

    # The page must load the script from that route rather than inline it.
    def test_onpremise_getting_started_web_references_core_js(self, client):
        response = client.get('/')
        self.assertIn(b'<script src="/51Degrees.core.js"></script>', response.data)


class OnPremiseGettingStartedWebConfigTests(unittest.TestCase):

    # A data file named in the environment replaces the one in config.json.
    def test_data_file_from_environment(self):
        with tempfile.NamedTemporaryFile(suffix=".hash", delete=False) as file:
            path = file.name
        try:
            with mock.patch.dict(os.environ, {ExampleUtils.DATA_FILE_ENV_VAR: path}):
                config = GettingStartedWeb.build_config()
            self.assertEqual(
                os.path.abspath(path),
                ExampleUtils.get_data_file_from_config(config))
        finally:
            os.remove(path)

    # A data file named in the environment that does not exist is reported by
    # name, rather than the example silently falling back to config.json.
    def test_missing_data_file_from_environment(self):
        missing = os.path.join(tempfile.gettempdir(), "no-such-51degrees-file.hash")
        with mock.patch.dict(os.environ, {ExampleUtils.DATA_FILE_ENV_VAR: missing}):
            with self.assertRaises(Exception) as context:
                GettingStartedWeb.build_config()
        self.assertIn(ExampleUtils.DATA_FILE_ENV_VAR, str(context.exception))

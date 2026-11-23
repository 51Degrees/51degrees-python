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
Requests the page of the on-premise getting started web example, through
Flask's test client, with the data file the example finds for itself, which
is the free Lite file. The example shares usage, as a web example should,
so sending is stood in for while the tests run and while the pipeline
closes, and no usage data leaves the machine the tests run on.
"""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.onpremise.gettingstarted_web \
    import app as example
from fiftyone_ipintelligence_shared.example_constants import \
    LITE_DATAFILE_NAME

# The address looked up, given as the example's client-ip query parameter.
CLIENT_IP = "8.8.8.8"

# The settings a fresh clone does not have, left out of the run of main.
SETTINGS = ("_51DEGREES_IPI_PATH", "_51DEGREES_LICENSE_KEY")

# What the example shows for a property its data file does not have.
NOT_FOUND = "Property not found in data file"


class OnPremiseGettingStartedWebTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sending = mock.patch("requests.post")
        cls.sending.start()
        cls.data_file = ExampleUtils.find_file(LITE_DATAFILE_NAME)
        if cls.data_file:
            example.build_pipeline(cls.data_file)

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.data_file:
                example.pipeline.close()
        finally:
            cls.sending.stop()
        super().tearDownClass()

    def setUp(self):
        if not self.data_file:
            self.fail(f"{LITE_DATAFILE_NAME} was neither found nor "
                      "downloaded, so the example has no data file.")
        self.client = example.app.test_client()

    def get_page(self):
        response = self.client.get(
            "/", query_string={"client-ip": CLIENT_IP})
        page = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code, page)
        return page

    def test_page_shows_the_registration_details(self):
        page = self.get_page()

        self.assertIn(f"IP address: {CLIENT_IP}", page)
        for label in ("Registered Name", "Registered Owner",
                      "Registered Country"):
            self.assertIn(f"<li>{label}: ", page)
        self.assertNotIn(NOT_FOUND, page)

    def test_the_pipeline_shares_usage(self):
        self.assertIn("shareusage", example.pipeline.flow_elements_list)

    def test_page_shows_the_countries_or_where_to_get_them(self):
        page = self.get_page()

        engine = example.pipeline.flow_elements_list["ip"]
        if ExampleUtils.has_property(engine, "CountryCodesGeographical"):
            self.assertIn(
                '<select id="CountryNamesGeographicalAllTranslated"', page)
        else:
            self.assertIn(
                f"The country dropdown {ExampleUtils.NEEDS_ENTERPRISE}", page)
            self.assertIn(example.CONTACT_US, page)


class OnPremiseGettingStartedWebMainTests(unittest.TestCase):

    def test_main_with_no_arguments(self):
        # main finds the free Lite file for itself, as from a fresh clone,
        # and serves the page until the server stops. Here the server
        # answers one request and stops.
        pages = []
        engines = []

        def serve(*args, **options):
            response = example.app.test_client().get(
                "/", query_string={"client-ip": CLIENT_IP})
            pages.append(response.get_data(as_text=True))
            engine = example.pipeline.flow_elements_list["ip"]
            engines.append((
                ExampleUtils.is_free_data_file(engine),
                ExampleUtils.has_property(
                    engine, "CountryCodesGeographical")))

        printed = io.StringIO()
        with mock.patch.dict(os.environ), redirect_stdout(printed), \
                mock.patch("requests.post"), \
                mock.patch.object(example.app, "run", side_effect=serve):
            for name in SETTINGS:
                os.environ.pop(name, None)
            example.main()

        self.assertEqual(1, len(pages))
        self.assertIn(f"IP address: {CLIENT_IP}", pages[0])
        self.assertIn("<li>Registered Name: ", pages[0])
        self.assertNotIn(NOT_FOUND, pages[0])
        free, has_countries = engines[0]
        self.assertTrue(free, "main did not use a free data file")
        if has_countries:
            self.assertIn(
                '<select id="CountryNamesGeographicalAllTranslated"',
                pages[0])
        else:
            self.assertIn(
                f"The country dropdown {ExampleUtils.NEEDS_ENTERPRISE}",
                pages[0])
            self.assertIn(example.CONTACT_US, pages[0])
        self.assertIn("Find out more:", printed.getvalue())


if __name__ == "__main__":
    unittest.main()

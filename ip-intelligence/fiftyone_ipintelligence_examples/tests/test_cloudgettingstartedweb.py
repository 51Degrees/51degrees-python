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
Requests the page of the cloud getting started web example, through Flask's
test client, against the live cloud service.
"""

import unittest

from fiftyone_ipintelligence_examples.cloud.gettingstarted_web \
    import app as example

from .live_cloud import find_resource_key, no_resource_key

NO_KEY = no_resource_key(
    "the ip product",
    "IP Intelligence properties such as RegisteredName")

# The address looked up, given as the example's client-ip query parameter.
CLIENT_IP = "8.8.8.8"

# What the example shows for a property the results do not have.
NOT_FOUND = "Property not found in data file"


class CloudGettingStartedWebTests(unittest.TestCase):

    resource_key = find_resource_key()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.resource_key:
            example.build_pipeline(cls.resource_key)

    @classmethod
    def tearDownClass(cls):
        if cls.resource_key:
            example.pipeline.close()
        super().tearDownClass()

    def setUp(self):
        if not self.resource_key:
            self.fail(NO_KEY)
        self.client = example.app.test_client()

    def test_page_shows_the_registration_details(self):
        response = self.client.get(
            "/", query_string={"client-ip": CLIENT_IP})
        page = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code, page)
        self.assertIn(f"IP address: {CLIENT_IP}", page)
        for label in ("Registered Name", "Registered Country"):
            self.assertIn(f"<li>{label}: ", page)
        self.assertNotIn(
            NOT_FOUND, page,
            "The cloud answered without a registration property, which is "
            "what a key that does not carry the ip product gets.")


if __name__ == "__main__":
    unittest.main()

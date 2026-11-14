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
The creator context demo, started with no resource key, stops and says
which environment variable to set and where to create a key.
"""

import unittest
from unittest import mock

from .test_creator_context_server import load_server

# A link to the page where a resource key is created, with the campaign
# tags every example's links carry.
CONFIGURE_LINK = (
    r"https://51degrees\.com/configure[^\s?]*\?utm_source=code"
    r"&utm_medium=example&utm_campaign=51degrees-python&utm_content=")


class CreatorContextWithoutKeyTests(unittest.TestCase):

    def test_says_where_to_create_a_resource_key(self):
        server = load_server()
        with mock.patch.object(server, "RESOURCE", None):
            with self.assertRaises(SystemExit) as stopped:
                server.run()
        said = str(stopped.exception.code)
        self.assertIn("_51DEGREES_RESOURCE_KEY", said)
        self.assertRegex(said, CONFIGURE_LINK)


if __name__ == "__main__":
    unittest.main()

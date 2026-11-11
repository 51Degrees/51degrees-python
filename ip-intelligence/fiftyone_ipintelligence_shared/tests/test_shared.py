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

import unittest

from fiftyone_ipintelligence_shared.constants import Constants
from fiftyone_ipintelligence_shared.utils import merge_two_dicts
from fiftyone_ipintelligence_shared.key_utils import KeyUtils


class SharedTests(unittest.TestCase):

    def test_evidence_keys(self):
        self.assertEqual(Constants.EVIDENCE_QUERY_CLIENT_IP_KEY, "query.client-ip")
        self.assertEqual(Constants.EVIDENCE_SERVER_CLIENT_IP_KEY, "server.client-ip")
        self.assertEqual(Constants.EVIDENCE_QUERY_CLIENT_IP_51D_KEY, "query.client-ip-51d")

    def test_merge_two_dicts(self):
        merged = merge_two_dicts({"a": 1, "b": 2}, {"b": 3, "c": 4})
        self.assertEqual(merged, {"a": 1, "b": 3, "c": 4})

    def test_get_named_key(self):
        import os
        os.environ["ipintelligencetestkey"] = "value"
        try:
            self.assertEqual(KeyUtils.get_named_key("ipintelligencetestkey"), "value")
        finally:
            del os.environ["ipintelligencetestkey"]


if __name__ == "__main__":
    unittest.main()

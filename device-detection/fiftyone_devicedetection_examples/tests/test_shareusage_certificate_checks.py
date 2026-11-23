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
The usage sharing example sends with certificate checks on, because it is the
code people copy into their own applications. The checks read the example's
source, so they need no data file and no network.
"""

import ast
import os
import unittest

EXAMPLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src",
    "fiftyone_devicedetection_examples", "onpremise", "shareusage.py")


class ShareUsageCertificateCheckTests(unittest.TestCase):

    def setUp(self):
        with open(EXAMPLE, encoding="utf-8") as source:
            self.tree = ast.parse(source.read())

    def test_does_not_replace_requests_post(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self.assertNotEqual("requests.post", ast.unparse(target))

    def test_does_not_turn_off_certificate_checks(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.keyword):
                self.assertNotEqual("verify", node.arg)
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    self.assertFalse(
                        isinstance(key, ast.Constant) and key.value == "verify")

    def test_does_not_silence_certificate_warnings(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                self.assertNotIn("disable_warnings", ast.unparse(node.func))


if __name__ == "__main__":
    unittest.main()

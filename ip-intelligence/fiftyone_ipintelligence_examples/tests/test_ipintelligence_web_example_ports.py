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
Each web example listens on port 5151 by default, rather than on the port
Flask picks when none is given. The checks read the examples' source, so
they start no server and need no data file and no network.
"""

import ast
import os
import unittest

EXAMPLES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src",
    "fiftyone_ipintelligence_examples")
WEB_EXAMPLES = [
    os.path.join(EXAMPLES, "cloud", "gettingstarted_web", "app.py"),
    os.path.join(EXAMPLES, "onpremise", "gettingstarted_web", "app.py"),
]


def read_port(node):
    # The default port, from a number, int() of one, or
    # os.environ.get(name, number).
    if isinstance(node, ast.Constant):
        return int(node.value)
    if isinstance(node, ast.Call):
        if getattr(node.func, "id", None) == "int" and node.args:
            return read_port(node.args[0])
        if getattr(node.func, "attr", None) == "get" and len(node.args) == 2:
            return read_port(node.args[1])
    return None


def default_port(path):
    # The port the example passes to app.run, or None when it passes none.
    with open(path, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"):
            for keyword in node.keywords:
                if keyword.arg == "port":
                    return read_port(keyword.value)
    return None


class WebExamplePortTests(unittest.TestCase):

    def test_every_web_example_listens_on_5151_by_default(self):
        for path in WEB_EXAMPLES:
            with self.subTest(example=path):
                self.assertEqual(5151, default_port(path))


if __name__ == "__main__":
    unittest.main()

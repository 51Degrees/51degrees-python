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
Each web example hands the whole web request to the pipeline with
webevidence, which adds it as server.http-request. The usage sharing element
accepts no Evidence and shares what it finds in that request, so an example
that adds only the Evidence its engine reads shares nothing else. The checks
read the examples' source, so they need no data file and no network.
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


def called_names(function):
    # The names of every function the given function calls.
    names = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            target = node.func
            names.add(target.attr if isinstance(target, ast.Attribute)
                      else getattr(target, "id", None))
    return names


class WebExamplesHandOverRequestTests(unittest.TestCase):

    def test_every_route_that_makes_flow_data_adds_the_web_request(self):
        for path in WEB_EXAMPLES:
            with open(path, encoding="utf-8") as source:
                tree = ast.parse(source.read())
            routes = [node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef)
                      and "create_flowdata" in called_names(node)]
            self.assertTrue(routes, path)
            for route in routes:
                with self.subTest(example=path, route=route.name):
                    self.assertIn("webevidence", called_names(route))


if __name__ == "__main__":
    unittest.main()

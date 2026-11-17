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
A Flow Data cannot be used by two threads at once. The FlowData class, the
web helpers and their readme say so, and so does every web example, which
also shows it by opening each Flow Data in a with statement, so that the
Flow Data belongs to the request that made it and is closed when that
request ends. The checks read the source and the documentation, so they
need no data file and no network.
"""

import ast
import os
import re
import unittest

from fiftyone_pipeline_core import web
from fiftyone_pipeline_core.flowdata import FlowData

PACKAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REPOSITORY = os.path.join(PACKAGE, "..", "..")

# What the web examples and the web helpers' documentation say.
ONE_THREAD = "flow data cannot be used by two threads at once"

# Folders that hold no examples of their own.
SKIPPED = {"__pycache__", "build", "cxx", "dist", "node_modules",
           "performance-tests", "tests", "tests_released", "venv"}


def words(text):
    # The text in lower case without comment markers or line breaks, so a
    # sentence reads the same however it is wrapped.
    return " ".join(re.sub(r"(?m)^\s*#+", " ", text).split()).lower()


def imports_web(tree):
    return any(isinstance(node, ast.ImportFrom)
               and node.module == "fiftyone_pipeline_core.web"
               for node in ast.walk(tree))


def web_examples():
    # Each Python file in an examples folder that uses the web helpers, as
    # its path from the repository root, its source and its syntax tree.
    found = []
    for root, folders, files in os.walk(REPOSITORY):
        folders[:] = [name for name in folders
                      if not name.startswith(".") and name not in SKIPPED]
        parts = os.path.relpath(root, REPOSITORY).split(os.sep)
        if not any(part == "examples" or part.endswith("_examples")
                   for part in parts):
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as file:
                source = file.read()
            tree = ast.parse(source)
            if imports_web(tree):
                found.append(
                    (os.path.relpath(path, REPOSITORY), source, tree))
    return sorted(found, key=lambda example: example[0])


class FlowDataThreadsDocumentationTests(unittest.TestCase):

    def test_the_flow_data_documentation_says_one_thread_at_a_time(self):
        text = words(FlowData.__doc__)
        for said in ("not safe to use from several threads at once",
                     "caller is responsible for any locking"):
            with self.subTest(said=said):
                self.assertTrue(said in text,
                                f"FlowData does not say '{said}'")

    def test_the_web_helpers_say_one_thread_at_a_time(self):
        self.assertTrue(ONE_THREAD in words(web.__doc__ or ""),
                        f"the web module does not say '{ONE_THREAD}'")

    def test_the_readme_says_one_thread_at_a_time(self):
        path = os.path.join(PACKAGE, "readme.md")
        with open(path, encoding="utf-8") as file:
            self.assertTrue(ONE_THREAD in words(file.read()),
                            f"readme.md does not say '{ONE_THREAD}'")

    def test_each_web_example_says_one_thread_at_a_time(self):
        examples = web_examples()
        self.assertTrue(examples, "no web examples found")
        for path, source, _ in examples:
            with self.subTest(example=path):
                self.assertTrue(ONE_THREAD in words(source),
                                f"does not say '{ONE_THREAD}'")

    def test_each_web_example_closes_its_flow_data_with_the_request(self):
        examples = web_examples()
        self.assertTrue(examples, "no web examples found")
        for path, _, tree in examples:
            calls = [node for node in ast.walk(tree)
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Attribute)
                     and node.func.attr == "create_flowdata"]
            opened = {id(item.context_expr) for node in ast.walk(tree)
                      if isinstance(node, ast.With) for item in node.items}
            with self.subTest(example=path):
                self.assertTrue(calls, "no Flow Data created")
                for call in calls:
                    self.assertIn(
                        id(call), opened,
                        f"line {call.lineno} creates a Flow Data outside a "
                        "with statement")


if __name__ == "__main__":
    unittest.main()

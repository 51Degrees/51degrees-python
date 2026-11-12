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

"""Checks that the two cloud examples still read the resource key under
the name its environment variable had before, when the new name is not set.

Importing an example runs it, which calls the cloud service, so the
function each example reads its key with is taken out of the example's
source and run on its own.
"""

import ast
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "cloud"

NEW_NAME = "_51DEGREES_RESOURCE_KEY"
OLD_NAME = "resource_key"


def reader(example):
    """The read_environment function of an example, or None when the
    example has none."""
    source = (EXAMPLES / example).read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) \
                and node.name == "read_environment":
            module = ast.Module(body=[node], type_ignores=[])
            names = {"os": os, "sys": sys}
            exec(compile(module, example, "exec"), names)
            return names["read_environment"]
    return None


class OldNameTests(unittest.TestCase):

    def setUp(self):
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(NEW_NAME, None)
        os.environ.pop(OLD_NAME, None)

    def read(self, example):
        """What the example reads for its resource key, and what it prints
        to the error stream."""
        read_environment = reader(example)
        self.assertIsNotNone(
            read_environment,
            example + " has no read_environment function, so it does not "
            "read the old name")
        # The example has to read the key through the function.
        self.assertIn(
            'read_environment("' + NEW_NAME + '", "' + OLD_NAME + '")',
            (EXAMPLES / example).read_text(encoding="utf-8"))
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            value = read_environment(NEW_NAME, OLD_NAME)
        return value, errors.getvalue()

    def test_resource_key_is_read_from_the_old_name(self):
        for example in ("gettingstarted.py", "web.py"):
            with self.subTest(example=example):
                os.environ[OLD_NAME] = "old-key"
                value, errors = self.read(example)
                self.assertEqual("old-key", value)
                self.assertIn(
                    OLD_NAME + " environment variable is deprecated", errors)
                self.assertIn(NEW_NAME, errors)

    def test_new_name_wins_and_nothing_is_printed(self):
        for example in ("gettingstarted.py", "web.py"):
            with self.subTest(example=example):
                os.environ[NEW_NAME] = "new-key"
                os.environ[OLD_NAME] = "old-key"
                value, errors = self.read(example)
                self.assertEqual("new-key", value)
                self.assertEqual("", errors)

    def test_neither_name_gives_none(self):
        for example in ("gettingstarted.py", "web.py"):
            with self.subTest(example=example):
                value, errors = self.read(example)
                self.assertIsNone(value)
                self.assertEqual("", errors)


if __name__ == "__main__":
    unittest.main()

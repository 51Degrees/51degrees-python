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

import ast
import os
import re
import unittest

# Each row is a name one package here imports from another package here,
# the package that holds it and the version of that package it came in at,
# so the importing package has to require at least that version. Without
# the minimum, pip leaves an older copy of the dependency in place when the
# importing package alone is upgraded, and the import fails. The test checks
# each import, the module holding each name and each requirement against the
# checkout. The version in each row is written here by hand, as the next
# release of the holding package after the last one without the name, and is
# not checked.
IMPORTED_NAMES = (
    ("pipeline/fiftyone_pipeline_engines",
     "fiftyone_pipeline_core",
     "4.5.44",
     "fiftyone_pipeline_core.elementdata",
     "_contents_property"),
    ("device-detection/fiftyone_devicedetection_cloud",
     "fiftyone_pipeline_core",
     "4.5.44",
     "fiftyone_pipeline_core.elementdata",
     "_CheckedDictWrites"),
    ("device-detection/fiftyone_devicedetection_onpremise",
     "fiftyone_pipeline_core",
     "4.5.44",
     "fiftyone_pipeline_core.elementdata_pool",
     "ElementDataPool"),
    ("ip-intelligence/fiftyone_ipintelligence_onpremise",
     "fiftyone_pipeline_core",
     "4.5.44",
     "fiftyone_pipeline_core.elementdata_pool",
     "ElementDataPool"),
)

# Where each package that holds one of the names above keeps its source.
PACKAGE_FOLDERS = {
    "fiftyone_pipeline_core": "pipeline/fiftyone_pipeline_core",
}

# A requirement that gives a minimum version, as setup.py writes one.
MINIMUM = re.compile(r"^>=\s*([0-9]+(?:\.[0-9]+)*)$")

# The name and the rest of one entry of an install_requires list.
REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)\s*(.*)$")

# The entries of an install_requires list, each in its own quotes.
QUOTED = re.compile("[\"']([^\"']+)[\"']")


def repository_root():
    """The folder holding ci/packages.json, found by walking up from this
    file, so the test reads the checkout it runs from."""
    folder = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isfile(os.path.join(folder, "ci", "packages.json")):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            raise AssertionError(
                "no ci/packages.json above " + os.path.abspath(__file__))
        folder = parent


def requirements(package_folder):
    """The install_requires of a package's setup.py, as the name required
    mapped to the rest of the requirement."""
    path = os.path.join(repository_root(), package_folder, "setup.py")
    with open(path, "rb") as file:
        text = file.read().decode("utf-8")
    found = re.search(r"install_requires\s*=\s*\[(.*?)\]", text, re.S)
    assert found is not None, "no install_requires in " + path
    out = {}
    for item in QUOTED.findall(found.group(1)):
        parts = REQUIREMENT.match(item.strip())
        if parts:
            out[parts.group(1)] = parts.group(2).strip()
    return out


def version_numbers(text):
    """A version as a tuple of its numbers, for comparing two of them."""
    return tuple(int(part) for part in text.split("."))


def imports_in(package_folder, module, name):
    """Whether any source file of the package imports the name from the
    module."""
    source = os.path.join(repository_root(), package_folder, "src")
    for folder, _, files in os.walk(source):
        if "cxx" in folder.split(os.sep):
            continue
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            with open(os.path.join(folder, file_name), "rb") as file:
                text = file.read().decode("utf-8", "replace")
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (isinstance(node, ast.ImportFrom)
                        and node.module == module
                        and any(alias.name == name
                                for alias in node.names)):
                    return True
    return False


def module_names(module):
    """The names a module of this checkout holds at its top level."""
    parts = module.split(".")
    path = os.path.join(repository_root(), PACKAGE_FOLDERS[parts[0]],
                        "src", *parts) + ".py"
    with open(path, "rb") as file:
        text = file.read().decode("utf-8")
    out = set()
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out.update(target.id for target in node.targets
                       if isinstance(target, ast.Name))
    return out


class PackageRequirementTests(unittest.TestCase):

    """A package that imports a name from another package here requires
    that package at the version the name came in at. Upgrading one package
    on its own then brings the dependency with it, where a requirement
    with no version leaves an older copy in place and the import fails."""

    def test_each_name_is_imported_where_the_row_says(self):
        for folder, _, _, module, name in IMPORTED_NAMES:
            with self.subTest(package=folder, name=name):
                self.assertTrue(
                    imports_in(folder, module, name),
                    "{0} does not import {1} from {2}".format(
                        folder, name, module))

    def test_each_name_is_held_by_the_package_the_row_names(self):
        for _, package, _, module, name in IMPORTED_NAMES:
            with self.subTest(package=package, name=name):
                self.assertEqual(package, module.split(".")[0])
                self.assertIn(name, module_names(module))

    def test_each_package_is_required_at_the_version_of_the_name(self):
        for folder, package, version, module, name in IMPORTED_NAMES:
            with self.subTest(package=folder, requires=package):
                required = requirements(folder)
                self.assertIn(
                    package, required,
                    "{0} imports {1} from {2} and does not require "
                    "{3}".format(folder, name, module, package))
                found = MINIMUM.match(required[package])
                self.assertIsNotNone(
                    found,
                    "{0} requires {1} as {2!r}, with no minimum "
                    "version".format(folder, package, required[package]))
                self.assertGreaterEqual(
                    version_numbers(found.group(1)),
                    version_numbers(version),
                    "{0} requires {1} {2}, below the {3} that holds "
                    "{4}".format(folder, package, required[package],
                                 version, name))


if __name__ == "__main__":
    unittest.main()

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
The derived property example needs no data file, no key and no network.
It is run here as a person runs it, from the command line, from a folder
other than its own and with none of the _51DEGREES_ environment variables
set. What it prints is checked for each of the four things it shows, being
a script held as text, a script read from a file, the same pipeline built
from a configuration file, and a request missing a source property, and for
the Find out more section it ends with. The example is also imported, and
the values its pipelines give are checked.
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest

from fiftyone_pipeline_derivedproperty import DerivedPropertyElement
from fiftyone_pipeline_derivedproperty.evaluate import USUAL_CAUSES

# The product folder. Each link's utm_content is the path of the example
# below this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))

EXAMPLES = os.path.join(
    PRODUCT, "fiftyone_pipeline_derivedproperty", "examples")

EXAMPLE = os.path.join(EXAMPLES, "derived_property.py")

# The module beside the example that holds the flow element giving the
# source properties.
SOURCE_MODULE = "screen_element"

# How long to wait for the example before failing, so a run that never
# ends cannot hold up the tests.
RUN_TIMEOUT_SECONDS = 120

# The start of the name of every 51Degrees environment variable. Each one is
# removed from the example's environment, to show it needs none of them.
SETTING_PREFIX = "_51DEGREES_"

# The heading of each part of the example, in the order it prints them.
TEXT_SCRIPT = "1. A script held in this example as text"
FILE_SCRIPT = "2. A script read from IsFullHd.yaml beside this example"
CONFIGURATION = "3. The same pipeline as 2, built from derived_property.json"
MISSING = "4. A request that gives no screen height"
PARTS = [TEXT_SCRIPT, FILE_SCRIPT, CONFIGURATION, MISSING]

# The screens the example gives, as a width and a height in pixels, with the
# values its two scripts give for each.
SCREENS = [
    (1920, 1080, "Large", True),
    (1024, 768, "Medium", False),
    (390, 844, "Small", False),
]

# The width the example gives with no height.
WIDTH_WITHOUT_HEIGHT = 1920

# The table each of the first three parts prints, as the words on each line.
SCREEN_SIZE_TABLE = [["Width", "Height", "ScreenSize"]] + [
    [str(width), str(height), size] for width, height, size, _ in SCREENS]
FULL_HD_TABLE = [["Width", "Height", "IsFullHd"]] + [
    [str(width), str(height), str(full_hd)]
    for width, height, _, full_hd in SCREENS]

# What ScreenSize says for a request that gives no screen height.
NO_HEIGHT_MESSAGE = (
    "Derived property 'ScreenSize' has no value because 1 source property "
    "was not available. 'screen.Height' (element 'screen' has no value for "
    "'Height': property not present on this request). " + USUAL_CAUSES)

# The heading of the Find out more section, and the line above it.
HEADING = "Find out more:"
RULE = "=" * 79

# A line of the section, which is a tab, a label and a link.
SECTION_LINE = re.compile(r"\t(?P<label>[^:\t]+): (?P<url>https://\S+)")

# A 51degrees.com link, which carries exactly these five parameters in
# this order.
TAGGED_LINK = re.compile(
    r"https://51degrees\.com/[^\s?]*"
    r"\?utm_source=code&utm_medium=example&utm_campaign=51degrees-python"
    r"&utm_content=(?P<content>[a-z0-9._-]+)"
    r"&utm_term=(?P<term>[a-z0-9._-]+)")

# Any link to 51degrees.com in what the example prints.
ANY_51DEGREES_LINK = re.compile(r"\S*51degrees\.com\S*")

# The repositories the section lists, as bare addresses.
REPOSITORIES = [
    "https://github.com/51Degrees/51degrees-python/tree/main/pipeline",
    "https://github.com/51Degrees/derived-properties",
    "https://github.com/51Degrees/specifications/tree/main/"
    "pipeline-specification",
]


def environment_without_settings():
    return {
        name: value for name, value in os.environ.items()
        if not name.upper().startswith(SETTING_PREFIX)}


def part(lines, heading):
    """The lines of one part of the output, after its heading and before
    the next heading or the Find out more section."""
    start = lines.index(heading) + 1
    end = start
    while end < len(lines) and lines[end] not in PARTS and \
            lines[end] != RULE:
        end += 1
    return lines[start:end]


def words(lines):
    """Each line that is not blank, as the words on it."""
    return [line.split() for line in lines if line.strip()]


class DerivedPropertyExampleOutputTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run from an empty folder, to show the example finds its script
        # file and configuration file from wherever it is run.
        with tempfile.TemporaryDirectory() as folder:
            cls.completed = subprocess.run(
                [sys.executable, EXAMPLE],
                capture_output=True, text=True, cwd=folder,
                env=environment_without_settings(),
                timeout=RUN_TIMEOUT_SECONDS)
        cls.lines = cls.completed.stdout.splitlines()

    def test_the_example_exits_cleanly(self):
        self.assertEqual(0, self.completed.returncode, self.completed.stderr)

    def test_the_example_shows_each_part_in_order(self):
        for heading in PARTS:
            self.assertIn(heading, self.lines, self.completed.stdout)
        found = [self.lines.index(heading) for heading in PARTS]
        self.assertEqual(sorted(found), found)

    def test_a_script_held_as_text_gives_the_screen_size(self):
        self.assertEqual(
            SCREEN_SIZE_TABLE, words(part(self.lines, TEXT_SCRIPT)))

    def test_a_script_read_from_a_file_gives_full_hd(self):
        self.assertEqual(FULL_HD_TABLE, words(part(self.lines, FILE_SCRIPT)))

    def test_the_configuration_file_gives_the_same_values(self):
        self.assertEqual(
            FULL_HD_TABLE, words(part(self.lines, CONFIGURATION)))

    def test_a_missing_height_shows_no_value_and_names_it(self):
        text = [line.strip() for line in part(self.lines, MISSING)
                if line.strip()]
        self.assertIn(
            f"The request gives a width of {WIDTH_WITHOUT_HEIGHT} and no "
            "height.", text)
        self.assertIn(
            "ScreenSize has_value() is False, and no_value_message() gives "
            "the reason.", text)
        # The message is wrapped to fit the console, so its lines are
        # joined to read it whole.
        first = next(index for index, line in enumerate(text)
                     if line.startswith("Derived property"))
        self.assertEqual(NO_HEIGHT_MESSAGE, " ".join(text[first:]))

    def test_the_example_ends_with_the_find_out_more_section(self):
        self.assertIn(HEADING, self.lines, self.completed.stdout)
        heading = self.lines.index(HEADING)
        self.assertEqual(RULE, self.lines[heading - 1])
        for line in PARTS:
            self.assertLess(self.lines.index(line), heading)
        section = self.lines[heading + 1:]
        self.assertTrue(section, "The section lists no links")
        for line in section:
            self.assertIsNotNone(SECTION_LINE.fullmatch(line), line)

    def test_every_51degrees_link_is_tagged(self):
        links = ANY_51DEGREES_LINK.findall(self.completed.stdout)
        self.assertTrue(links, "The example prints no 51degrees.com link")
        content = os.path.relpath(EXAMPLE, PRODUCT).replace(os.sep, "-")
        for link in links:
            tagged = TAGGED_LINK.fullmatch(link)
            self.assertIsNotNone(tagged, link)
            self.assertEqual(content, tagged.group("content"))
            self.assertLessEqual(len(tagged.group("term")), 60)
            self.assertTrue(
                tagged.group("term").startswith("find-out-more"), link)

    def test_the_section_lists_the_repositories(self):
        heading = self.lines.index(HEADING)
        urls = [SECTION_LINE.fullmatch(line).group("url")
                for line in self.lines[heading + 1:]
                if SECTION_LINE.fullmatch(line)]
        for repository in REPOSITORIES:
            self.assertIn(repository, urls)


class DerivedPropertyExampleValueTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Python puts the folder of the file it runs first on its path,
        # which is how the example finds the module beside it. The same is
        # done here for as long as these tests use the example.
        sys.path.insert(0, EXAMPLES)
        cls.addClassCleanup(sys.path.remove, EXAMPLES)
        cls.addClassCleanup(sys.modules.pop, SOURCE_MODULE, None)
        spec = importlib.util.spec_from_file_location(
            "derived_property_example", EXAMPLE)
        cls.example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.example)

    def test_the_text_script_gives_each_screen_size(self):
        with self.example.pipeline_from_text() as pipeline:
            for width, height, size, _ in SCREENS:
                value = self.example.value_of(
                    pipeline, "ScreenSize", width, height)
                self.assertTrue(value.has_value(), value.no_value_message())
                self.assertEqual(size, value.value())

    def test_the_file_script_says_whether_each_screen_is_full_hd(self):
        with self.example.pipeline_from_file() as pipeline:
            for width, height, _, full_hd in SCREENS:
                value = self.example.value_of(
                    pipeline, "IsFullHd", width, height)
                self.assertTrue(value.has_value(), value.no_value_message())
                self.assertIs(full_hd, value.value())

    def test_the_configuration_file_builds_the_same_pipeline(self):
        with self.example.pipeline_from_file() as from_file, \
                self.example.pipeline_from_configuration() as configured:
            self.assertEqual(
                [type(element) for element in from_file.flow_elements],
                [type(element) for element in configured.flow_elements])
            derived = configured.get_element("derived")
            self.assertIsInstance(derived, DerivedPropertyElement)
            self.assertEqual(
                ["IsFullHd"], [script.name for script in derived.scripts])
            for width, height, _, full_hd in SCREENS:
                value = self.example.value_of(
                    configured, "IsFullHd", width, height)
                self.assertIs(full_hd, value.value())

    def test_building_from_the_configuration_file_keeps_the_folder(self):
        folder = os.getcwd()
        with self.example.pipeline_from_configuration():
            self.assertEqual(folder, os.getcwd())

    def test_a_request_without_a_height_has_no_value_and_says_why(self):
        with self.example.pipeline_from_text() as pipeline:
            value = self.example.value_of(
                pipeline, "ScreenSize", WIDTH_WITHOUT_HEIGHT)
        self.assertFalse(value.has_value())
        self.assertEqual(NO_HEIGHT_MESSAGE, value.no_value_message())
        # Reading the value raises the same message.
        with self.assertRaises(Exception) as raised:
            value.value()
        self.assertEqual(NO_HEIGHT_MESSAGE, str(raised.exception))


if __name__ == "__main__":
    unittest.main()

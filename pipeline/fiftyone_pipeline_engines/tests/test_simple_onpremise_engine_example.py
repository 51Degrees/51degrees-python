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
The on-premise engine example reads its star signs from the small data file
beside it, so it needs no downloaded data file, no key and no network. It is
run here as a person runs it, from the command line, with none of the
_51DEGREES_ environment variables set. What it prints is checked, being the
star signs and the Find out more section it ends with. It is also run with a
changed copy of its data file, to show the answers come from the file.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest

# The product folder. Each link's utm_content is the path of the example
# below this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))

EXAMPLES = os.path.join(PRODUCT, "fiftyone_pipeline_engines", "examples")

EXAMPLE = os.path.join(EXAMPLES, "simple_onpremise_engine.py")

# The data file the example reads when it is given none.
DATA_FILE = os.path.join(EXAMPLES, "starsigns.csv")

# How long to wait for the example before failing, so a run that never
# ends cannot hold up the tests.
RUN_TIMEOUT_SECONDS = 120

# The start of the name of every 51Degrees environment variable. Each one is
# removed from the example's environment, to show it needs none of them.
SETTING_PREFIX = "_51DEGREES_"

# What the example prints for each date of birth it looks up.
STAR_SIGNS = [
    "With a date of birth of 1992-12-18, your star sign is Sagittarius.",
    "With a date of birth of 1990-12-25, your star sign is Capricorn.",
    "With a date of birth of 1992-04-15, your star sign is Aries.",
]

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
    "https://github.com/51Degrees/51degrees-python/tree/main/"
    "device-detection",
    "https://github.com/51Degrees/specifications/tree/main/"
    "pipeline-specification",
]


def environment_without_settings():
    return {
        name: value for name, value in os.environ.items()
        if not name.upper().startswith(SETTING_PREFIX)}


def run_example(*arguments):
    return subprocess.run(
        [sys.executable, EXAMPLE, *arguments],
        capture_output=True, text=True,
        env=environment_without_settings(),
        timeout=RUN_TIMEOUT_SECONDS)


class SimpleOnPremiseEngineExampleTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.completed = run_example()
        cls.lines = cls.completed.stdout.splitlines()

    def test_the_example_exits_cleanly(self):
        self.assertEqual(0, self.completed.returncode, self.completed.stderr)

    def test_the_example_prints_each_star_sign(self):
        for line in STAR_SIGNS:
            self.assertIn(line, self.lines, self.completed.stdout)

    def test_the_example_ends_with_the_find_out_more_section(self):
        self.assertIn(HEADING, self.lines, self.completed.stdout)
        heading = self.lines.index(HEADING)
        self.assertEqual(RULE, self.lines[heading - 1])
        for line in STAR_SIGNS:
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

    def test_the_star_signs_come_from_the_data_file(self):
        # A copy of the data file with one star sign renamed, given to the
        # example as its first argument.
        with open(DATA_FILE, encoding="utf-8") as source:
            table = source.read()
        self.assertIn("Sagittarius", table)
        with tempfile.TemporaryDirectory() as folder:
            changed = os.path.join(folder, "starsigns.csv")
            with open(changed, "w", encoding="utf-8") as target:
                target.write(table.replace("Sagittarius", "The Archer"))

            completed = run_example(changed)

        self.assertEqual(0, completed.returncode, completed.stderr)
        lines = completed.stdout.splitlines()
        self.assertIn(
            "With a date of birth of 1992-12-18, your star sign is "
            "The Archer.", lines)
        self.assertIn(STAR_SIGNS[1], lines)
        self.assertIn(STAR_SIGNS[2], lines)


if __name__ == "__main__":
    unittest.main()

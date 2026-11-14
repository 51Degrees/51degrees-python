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
The cloud engine example starts a star sign service of its own on this
machine, so it needs no key and no network. It is run here as a person runs
it, from the command line, with none of the _51DEGREES_ environment
variables set, so a key or endpoint set for the other tests cannot reach it.
What it prints is checked, being the star signs, the reason the service
gives when there is no date of birth, and the Find out more section it ends
with.
"""

import os
import re
import subprocess
import sys

import pytest

# The product folder. Each link's utm_content is the path of the example
# below this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

EXAMPLE = os.path.join(
    PRODUCT, "fiftyone_pipeline_cloudrequestengine", "examples", "src",
    "fiftyone_pipeline_examples", "cloud", "simple_cloud_engine.py")

# The example as the readme runs it.
MODULE = "fiftyone_pipeline_examples.cloud.simple_cloud_engine"

# How long to wait for the example before failing, so a run that never
# ends cannot hold up the tests.
RUN_TIMEOUT_SECONDS = 120

# The start of the name of every 51Degrees environment variable. Each one is
# removed from the example's environment, to show it needs none of them.
SETTING_PREFIX = "_51DEGREES_"

# What the example prints for each date of birth it looks up, and for the
# request with none.
STAR_SIGNS = [
    "With a date of birth of 1992-12-18, your star sign is Sagittarius.",
    "With a date of birth of 1990-12-25, your star sign is Capricorn.",
    "With a date of birth of 1992-04-15, your star sign is Aries.",
    "With no date of birth, there is no star sign. The service needs a "
    "date of birth in the form YYYY-MM-DD to find a star sign.",
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


@pytest.fixture(scope="module")
def completed():
    environment = {
        name: value for name, value in os.environ.items()
        if not name.upper().startswith(SETTING_PREFIX)}
    return subprocess.run(
        [sys.executable, "-m", MODULE],
        capture_output=True, text=True, env=environment,
        timeout=RUN_TIMEOUT_SECONDS)


def section_of(lines):
    return lines[lines.index(HEADING) + 1:]


def test_the_example_exits_cleanly(completed):
    assert completed.returncode == 0, completed.stderr


def test_the_example_prints_each_star_sign(completed):
    lines = completed.stdout.splitlines()
    for line in STAR_SIGNS:
        assert line in lines, completed.stdout


def test_the_example_ends_with_the_find_out_more_section(completed):
    lines = completed.stdout.splitlines()
    assert HEADING in lines, completed.stdout
    heading = lines.index(HEADING)
    assert lines[heading - 1] == RULE
    for line in STAR_SIGNS:
        assert lines.index(line) < heading
    section = section_of(lines)
    assert section, "The section lists no links"
    for line in section:
        assert SECTION_LINE.fullmatch(line), line


def test_every_51degrees_link_is_tagged(completed):
    links = ANY_51DEGREES_LINK.findall(completed.stdout)
    assert links, "The example prints no 51degrees.com link"
    content = os.path.relpath(EXAMPLE, PRODUCT).replace(os.sep, "-")
    for link in links:
        tagged = TAGGED_LINK.fullmatch(link)
        assert tagged, link
        assert tagged.group("content") == content
        assert len(tagged.group("term")) <= 60
        assert tagged.group("term").startswith("find-out-more"), link


def test_the_section_lists_the_repositories(completed):
    urls = [SECTION_LINE.fullmatch(line).group("url")
            for line in section_of(completed.stdout.splitlines())
            if SECTION_LINE.fullmatch(line)]
    for repository in REPOSITORIES:
        assert repository in urls

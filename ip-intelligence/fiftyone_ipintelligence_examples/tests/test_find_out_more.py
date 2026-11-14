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
Every example ends with a "Find out more" section, which gives the person
running it links to follow up, wherever the example ends. The first checks
read the examples' source. The others run each example to an early end, with
no resource key or no data file, so none of them needs a key, a data file or
the network.
"""

import io
import os
import re
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.cloud import (
    countries_console as cloud_countries_console)
from fiftyone_ipintelligence_examples.cloud import getallproperties_console
from fiftyone_ipintelligence_examples.cloud.gettingstarted_web import (
    app as cloud_gettingstarted_web)
from fiftyone_ipintelligence_examples.cloud import (
    gettingstarted_console as cloud_gettingstarted_console)
from fiftyone_ipintelligence_examples.cloud import (
    metadata_console as cloud_metadata_console)
from fiftyone_ipintelligence_examples.cloud import (
    mixed_console as cloud_mixed_console)
from fiftyone_ipintelligence_examples.onpremise import compare_console
from fiftyone_ipintelligence_examples.onpremise import countries_console
from fiftyone_ipintelligence_examples.onpremise import datafileupdate_console
from fiftyone_ipintelligence_examples.onpremise import gettingstarted_console
from fiftyone_ipintelligence_examples.onpremise import metadata_console
from fiftyone_ipintelligence_examples.onpremise import mixed_console
from fiftyone_ipintelligence_examples.onpremise import offlineprocessing
from fiftyone_ipintelligence_examples.onpremise import performance_console

# The product folder. Each link's utm_content is the path of its file below
# this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EXAMPLES = os.path.join(
    PRODUCT, "fiftyone_ipintelligence_examples", "src",
    "fiftyone_ipintelligence_examples")
CLOUD = os.path.join(EXAMPLES, "cloud")
ONPREMISE = os.path.join(EXAMPLES, "onpremise")

# Every file that holds a section. A web example builds its page in its app,
# so the app holds the section for the page.
SOURCES = [
    os.path.join(CLOUD, "countries_console.py"),
    os.path.join(CLOUD, "getallproperties_console.py"),
    os.path.join(CLOUD, "gettingstarted_console.py"),
    os.path.join(CLOUD, "gettingstarted_web", "app.py"),
    os.path.join(CLOUD, "metadata_console.py"),
    os.path.join(CLOUD, "mixed_console.py"),
    os.path.join(ONPREMISE, "compare_console.py"),
    os.path.join(ONPREMISE, "countries_console.py"),
    os.path.join(ONPREMISE, "datafileupdate_console.py"),
    os.path.join(ONPREMISE, "gettingstarted_console.py"),
    os.path.join(ONPREMISE, "gettingstarted_web", "app.py"),
    os.path.join(ONPREMISE, "metadata_console.py"),
    os.path.join(ONPREMISE, "mixed_console.py"),
    os.path.join(ONPREMISE, "offlineprocessing.py"),
    os.path.join(ONPREMISE, "performance_console.py"),
    os.path.join(
        PRODUCT, "fiftyone_ipintelligence", "examples", "gettingstarted.py"),
]

# The name of the section, or of the list that holds its links.
SECTION_NAME = re.compile(r"(?i)find[ _]out[ _]more")

# A 51degrees.com link in the section, which carries a utm_term that starts
# with "find-out-more".
SECTION_LINK = re.compile(
    r"https://51degrees\.com/[^\s\"'<>)]*utm_term=find-out-more[^\s\"'<>)]*")

# This product's folder in the repository, which every section links to.
REPOSITORY = (
    "https://github.com/51Degrees/51degrees-python/tree/main/"
    "ip-intelligence")

# The settings that let an example get past its early end.
SETTINGS = [
    "_51DEGREES_RESOURCE_KEY", "resource_key", "RESOURCE_KEY",
    "_51DEGREES_LICENSE_KEY", "license_key",
    ExampleUtils.IPI_PATH_ENV_VAR, ExampleUtils.DATA_FILE_ENV_VAR]


def slug(path):
    """The utm_content of a link in the file, which is the path below the
    product folder with each separator a hyphen."""
    return os.path.relpath(path, PRODUCT).replace(os.sep, "-")


def printed_by(run):
    """Runs an example with the settings taken out of the environment, and
    returns what it printed."""
    printed = io.StringIO()
    with mock.patch.dict(os.environ), redirect_stdout(printed):
        for name in SETTINGS:
            os.environ.pop(name, None)
        run()
    return printed.getvalue()


class FindOutMoreSourceTests(unittest.TestCase):

    def test_every_example_has_a_find_out_more_section(self):
        for path in SOURCES:
            with self.subTest(example=slug(path)):
                with open(path, encoding="utf-8") as source:
                    # A page separates the parameters with "&amp;".
                    text = source.read().replace("&amp;", "&")
                self.assertRegex(text, SECTION_NAME)
                links = SECTION_LINK.findall(text)
                self.assertTrue(
                    links, "The section has no tagged 51degrees.com link")
                for link in links:
                    self.assertIn(f"&utm_content={slug(path)}&", link)
                self.assertIn(REPOSITORY, text)


class FindOutMoreAtEarlyEndsTests(unittest.TestCase):

    def test_cloud_examples_without_a_resource_key(self):
        examples = {
            "countries_console": cloud_countries_console.main,
            "getallproperties_console": getallproperties_console.main,
            "gettingstarted_console": cloud_gettingstarted_console.main,
            "metadata_console": cloud_metadata_console.main,
            "mixed_console": cloud_mixed_console.main,
        }
        for name, main in examples.items():
            with self.subTest(example=name):
                self.assertIn("Find out more:", printed_by(lambda: main([])))

    def test_cloud_web_example_when_its_server_stops(self):
        # The pipeline and the server are stood in for, so main returns at
        # once, as it does when the server stops.
        web = cloud_gettingstarted_web
        with mock.patch.object(web, "build_pipeline"),                 mock.patch.object(web.app, "run"):
            self.assertIn(
                "Find out more:", printed_by(lambda: web.main("a key")))

    def test_onpremise_examples_without_a_data_file(self):
        examples = {
            "compare_console": compare_console.main,
            "countries_console": countries_console.main,
            "datafileupdate_console": datafileupdate_console.main,
            "gettingstarted_console": gettingstarted_console.main,
            "metadata_console": metadata_console.main,
            "mixed_console": mixed_console.main,
            "offlineprocessing": offlineprocessing.main,
            "performance_console": performance_console.main,
        }
        for name, main in examples.items():
            with self.subTest(example=name):
                with mock.patch.object(
                        ExampleUtils, "find_file", return_value=None):
                    printed = printed_by(lambda: main([]))
                self.assertIn("Find out more:", printed)


if __name__ == "__main__":
    unittest.main()

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
import runpy
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_examples.cloud import configurator_console
from fiftyone_devicedetection_examples.cloud import (
    gettingstarted_console as cloud_gettingstarted_console)
from fiftyone_devicedetection_examples.cloud import (
    metadata_console as cloud_metadata_console)
from fiftyone_devicedetection_examples.cloud import nativemodellookup_console
from fiftyone_devicedetection_examples.cloud import taclookup_console
from fiftyone_devicedetection_examples.cloud.gettingstarted_web import (
    app as cloud_gettingstarted_web)
from fiftyone_devicedetection_examples.cloud.useragentclienthints_web import (
    app as cloud_useragentclienthints_web)
from fiftyone_devicedetection_examples.onpremise import gettingstarted_console
from fiftyone_devicedetection_examples.onpremise import match_metrics
from fiftyone_devicedetection_examples.onpremise import metadata_console
from fiftyone_devicedetection_examples.onpremise import shareusage

# The product folder. Each link's utm_content is the path of its file below
# this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EXAMPLES = os.path.join(
    PRODUCT, "fiftyone_devicedetection_examples", "src",
    "fiftyone_devicedetection_examples")
CLOUD = os.path.join(EXAMPLES, "cloud")
ONPREMISE = os.path.join(EXAMPLES, "onpremise")

# Every file that holds a section. A web example has one in its page, and
# one in its app for the console.
SOURCES = [
    os.path.join(CLOUD, "configurator_console.py"),
    os.path.join(CLOUD, "failuretomatch.py"),
    os.path.join(CLOUD, "gettingstarted_console.py"),
    os.path.join(CLOUD, "gettingstarted_web", "app.py"),
    os.path.join(CLOUD, "gettingstarted_web", "templates", "index.html"),
    os.path.join(CLOUD, "metadata_console.py"),
    os.path.join(CLOUD, "nativemodellookup_console.py"),
    os.path.join(CLOUD, "taclookup_console.py"),
    os.path.join(CLOUD, "useragentclienthints_web", "app.py"),
    os.path.join(
        CLOUD, "useragentclienthints_web", "templates", "index.html"),
    os.path.join(ONPREMISE, "csv_profile_metadata.py"),
    os.path.join(ONPREMISE, "datafileupdate_console.py"),
    os.path.join(ONPREMISE, "failuretomatch.py"),
    os.path.join(ONPREMISE, "gettingstarted_console.py"),
    os.path.join(ONPREMISE, "gettingstarted_web", "app.py"),
    os.path.join(ONPREMISE, "gettingstarted_web", "templates", "index.html"),
    os.path.join(ONPREMISE, "match_metrics.py"),
    os.path.join(ONPREMISE, "metadata_console.py"),
    os.path.join(ONPREMISE, "offlineprocessing.py"),
    os.path.join(ONPREMISE, "performance.py"),
    os.path.join(ONPREMISE, "profile_metadata_console.py"),
    os.path.join(ONPREMISE, "shareusage.py"),
    os.path.join(ONPREMISE, "useragentclienthints_web", "app.py"),
    os.path.join(
        ONPREMISE, "useragentclienthints_web", "templates", "index.html"),
    os.path.join(
        PRODUCT, "fiftyone_devicedetection", "examples", "gettingstarted.py"),
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
    "device-detection")

# The settings that let an example get past its early end.
SETTINGS = [
    "_51DEGREES_RESOURCE_KEY", "resource_key", "RESOURCE_KEY",
    "_51DEGREES_LICENSE_KEY", "license_key", "LICENSE_KEY"]


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
            "configurator_console": configurator_console.main,
            "gettingstarted_console": cloud_gettingstarted_console.main,
            "metadata_console": cloud_metadata_console.main,
            "nativemodellookup_console": nativemodellookup_console.main,
            "taclookup_console": taclookup_console.main,
            "gettingstarted_web": cloud_gettingstarted_web.main,
            "useragentclienthints_web": cloud_useragentclienthints_web.main,
        }
        for name, main in examples.items():
            with self.subTest(example=name):
                self.assertIn("Find out more:", printed_by(lambda: main([])))

    def test_cloud_failuretomatch_without_a_resource_key(self):
        # This example has no main, and runs when it is run as a script.
        printed = printed_by(lambda: runpy.run_module(
            "fiftyone_devicedetection_examples.cloud.failuretomatch",
            run_name="__main__"))
        self.assertIn("Find out more:", printed)

    def test_onpremise_examples_without_a_data_file(self):
        examples = {
            "gettingstarted_console": gettingstarted_console.main,
            "match_metrics": match_metrics.main,
            "metadata_console": metadata_console.main,
            "shareusage": shareusage.main,
        }
        for name, main in examples.items():
            with self.subTest(example=name):
                with mock.patch.object(
                        ExampleUtils, "find_file", return_value=None):
                    printed = printed_by(lambda: main([]))
                self.assertIn("Find out more:", printed)


if __name__ == "__main__":
    unittest.main()

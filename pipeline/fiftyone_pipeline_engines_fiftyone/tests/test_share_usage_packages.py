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
The Package elements of a usage sharing record. A record that carries the
invariant values names every 51Degrees package in use with its version.
"""

import gzip
import re
import unittest
from importlib import metadata
from unittest import mock

import requests

from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The package size is never reached, so the element keeps what it would
# share and sends nothing until it is closed.
QUEUE_ONLY = {
    "requested_package_size": 1000,
    "endpoint": "http://127.0.0.1:9",
}

# The packages a Pipeline holding only usage sharing uses, being the one
# holding the Pipeline, the one holding the element and the one that
# requires.
USAGE_SHARING_PACKAGES = (
    "fiftyone_pipeline_core",
    "fiftyone_pipeline_engines",
    "fiftyone_pipeline_engines_fiftyone",
)


def canonical(name):
    """A package name as the package index compares names."""
    return re.sub(r"[-_.]+", "_", name).lower()


def sent_on_close(usage):
    """Closes the element, which sends what it has queued, and returns each
    record it posted. The post is answered without leaving the process."""
    sent = []

    def post(url, headers=None, data=None, **kwargs):
        sent.append(gzip.decompress(data).decode("utf8"))
        return mock.Mock(status_code=200, text="")

    with mock.patch.object(requests, "post", post):
        usage.close()
    return [record for message in sent
            for record in re.findall(r"<Device>.*?</Device>", message)]


def records_of(usage, requests_evidence, *elements):
    """Processes each request's Evidence through a Pipeline holding the
    elements and the usage sharing element, and returns the records sent."""
    builder = PipelineBuilder(NO_DEFAULT_ELEMENTS)
    for element in elements:
        builder.add(element)
    pipeline = builder.add(usage).build()
    for evidence in requests_evidence:
        flowdata = pipeline.create_flowdata()
        for key, value in evidence.items():
            flowdata.evidence.add(key, value)
        flowdata.process()
    return sent_on_close(usage)


def packages_in(record):
    """The Package elements of a record, as name and version pairs."""
    return re.findall(r'<Package Name="([^"]*)">([^<]*)</Package>', record)


class StarSign(FlowElement):
    """An element from no installed package."""

    def __init__(self):
        super(StarSign, self).__init__()
        self.datakey = "starsign"

    def process_internal(self, flow_data):
        pass


class PackageTests(unittest.TestCase):
    """A record that carries the invariant values names every 51Degrees
    package in use with its version (usage-sharing-element.md lines 313 to
    321 at d79bbe3b)."""

    def test_the_first_record_names_every_51degrees_package_in_use(self):
        # The packages are invariant values, so the record after the first,
        # written within the hour, names none (usage-sharing-element.md
        # lines 181 to 209 at d79bbe3b).
        usage = ShareUsage(**QUEUE_ONLY)
        # A record written before the lookup of the server's address ends
        # does not count as carrying them, so wait for it.
        usage._server_ip_found.wait(10)
        records = records_of(usage, [
            {"header.user-agent": "first"},
            {"header.user-agent": "second"},
        ])

        self.assertEqual(2, len(records))
        packages = packages_in(records[0])
        self.assertEqual(
            sorted(USAGE_SHARING_PACKAGES),
            sorted(canonical(name) for name, _ in packages))
        for name, version in packages:
            self.assertEqual(metadata.version(name), version, name)
        self.assertEqual([], packages_in(records[1]))

    def test_packages_follow_the_flow_elements(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}])[0]

        self.assertRegex(
            record,
            r"</FlowElement>(<Package [^>]*>[^<]*</Package>)+<Language>")

    def test_an_element_from_no_package_names_no_package(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}], StarSign())[0]

        self.assertIn("<FlowElement>StarSign</FlowElement>", record)
        self.assertEqual(
            sorted(USAGE_SHARING_PACKAGES),
            sorted(canonical(name) for name, _ in packages_in(record)))

    def test_packages_that_are_not_51degrees_are_not_named(self):
        record = records_of(ShareUsage(**QUEUE_ONLY), [
            {"header.user-agent": "agent value"}])[0]

        names = [canonical(name) for name, _ in packages_in(record)]
        # A record that named no package would pass the checks below.
        self.assertIn("fiftyone_pipeline_core", names)
        for other in ("requests", "cachetools", "flask"):
            self.assertNotIn(other, names)


if __name__ == "__main__":
    unittest.main()

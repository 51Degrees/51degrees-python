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

"""A configuration file gives a list of names as one comma-separated string,
so the usage sharing element takes its query string parameters to share and
its headers not to share in that form, as well as in a list."""

import json
import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

# No JavaScript or set header elements, so the pipeline holds the usage
# sharing element alone.
NO_DEFAULT_ELEMENTS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# The package size is never reached, so the element keeps what it would
# share and sends nothing.
QUEUE_ONLY = {
    "requested_package_size": 1000,
    "endpoint": "http://127.0.0.1:9",
}

# Shares only the query string parameters listed and those starting 51D_,
# where every one is shared by default.
LISTED_ONLY = {"share_all_query_string_parameters": False}

# A configuration file that gives both lists as comma-separated strings.
CONFIGURATION = """
{
  "PipelineOptions": {
    "Elements": [
      {
        "elementName": "ShareUsage",
        "elementPath": "fiftyone_pipeline_engines_fiftyone.share_usage",
        "elementParameters": {
          "requested_package_size": 1000,
          "endpoint": "http://127.0.0.1:9",
          "share_all_query_string_parameters": false,
          "query_whitelist": "first,second",
          "header_blacklist": "x-one, x-two"
        }
      }
    ]
  }
}
"""

EVIDENCE = {
    "query.first": "first value",
    "query.second": "second value",
    "query.third": "third value",
    # Named by one letter of the parameters to share.
    "query.f": "letter value",
    "header.user-agent": "agent value",
    "header.x-one": "one value",
    "header.x-two": "two value",
}


def shared_by(pipeline, usage):
    """Processes the evidence above and returns what the usage sharing
    element queued to share."""

    flowdata = pipeline.create_flowdata()
    for key, value in EVIDENCE.items():
        flowdata.evidence.add(key, value)
    flowdata.process()
    return "".join(usage.share_data)


def shared_alone_by(usage):
    """What the usage sharing element shares in a pipeline of its own."""

    pipeline = PipelineBuilder(NO_DEFAULT_ELEMENTS).add(usage).build()
    return shared_by(pipeline, usage)


class ShareUsageListTests(unittest.TestCase):

    def assert_shared(self, shared, values):
        for value in values:
            self.assertIn(value, shared)

    def assert_not_shared(self, shared, values):
        for value in values:
            self.assertNotIn(value, shared)

    def test_query_parameters_to_share_from_a_string(self):
        shared = shared_alone_by(
            ShareUsage(query_whitelist="first,second", **LISTED_ONLY,
                       **QUEUE_ONLY))

        self.assert_shared(shared, ("first value", "second value"))
        self.assert_not_shared(shared, ("third value", "letter value"))

    def test_headers_not_to_share_from_a_string(self):
        shared = shared_alone_by(
            ShareUsage(header_blacklist="x-one, x-two", **QUEUE_ONLY))

        self.assert_shared(shared, ("agent value",))
        self.assert_not_shared(shared, ("one value", "two value"))

    def test_lists_from_a_configuration_file(self):
        pipeline = PipelineBuilder().build_from_configuration(
            json.loads(CONFIGURATION))
        usage = pipeline.get_element("shareusage")
        shared = shared_by(pipeline, usage)

        self.assert_shared(
            shared, ("first value", "second value", "agent value"))
        self.assert_not_shared(
            shared, ("third value", "letter value", "one value", "two value"))

    def test_names_are_trimmed_and_empty_entries_left_out(self):
        usage = ShareUsage(
            query_whitelist=" first , ,second,",
            header_blacklist=",x-one,, x-two ",
            **QUEUE_ONLY)

        self.assertEqual(["first", "second"], usage.query_whitelist)
        self.assertEqual(["x-one", "x-two"], usage.header_blacklist)

    def test_an_empty_string_is_an_empty_list(self):
        usage = ShareUsage(
            query_whitelist="", header_blacklist="", **LISTED_ONLY,
            **QUEUE_ONLY)

        self.assertEqual([], usage.query_whitelist)
        self.assertEqual([], usage.header_blacklist)
        shared = shared_alone_by(usage)
        self.assert_shared(shared, ("agent value", "one value"))
        self.assert_not_shared(shared, ("first value",))

    def test_a_list_is_used_as_it_is(self):
        names = ["first", "second"]
        headers = ["x-one", "x-two"]
        usage = ShareUsage(
            query_whitelist=names, header_blacklist=headers,
            **LISTED_ONLY, **QUEUE_ONLY)

        self.assertIs(names, usage.query_whitelist)
        self.assertIs(headers, usage.header_blacklist)
        shared = shared_alone_by(usage)
        self.assert_shared(
            shared, ("first value", "second value", "agent value"))
        self.assert_not_shared(
            shared, ("third value", "letter value", "one value", "two value"))


if __name__ == "__main__":
    unittest.main()

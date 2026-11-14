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

"""Runs the usage sharing example, examples/usagesharing/usagesharing.py,
which builds a pipeline from its 51d.json. Evidence is then processed with
that pipeline, with requests.post replaced so that nothing is sent, and the
test checks what would have been sent."""

import gzip
import importlib.util
import inspect
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

EXAMPLE = (Path(__file__).resolve().parents[1] / "examples" /
           "usagesharing" / "usagesharing.py")

# Where usage data goes when no endpoint is given, as in the example.
DEFAULT_ENDPOINT = inspect.signature(
    ShareUsage.__init__).parameters["endpoint"].default

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# An address from the range kept for documentation, RFC 5737.
CLIENT_IP = "203.0.113.42"


def load_example():
    """Runs the example's file as a module and returns the module."""
    spec = importlib.util.spec_from_file_location(
        "usagesharing_example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UsageSharingExampleTests(unittest.TestCase):

    def test_pipeline_shares_what_it_processes(self):
        messages = []

        def post(url, headers=None, data=None, **options):
            messages.append({
                "url": url,
                "body": gzip.decompress(data).decode("utf-8"),
                "options": options,
            })
            return mock.Mock(status_code=200, text="")

        printed = io.StringIO()
        with mock.patch("requests.post", side_effect=post), \
                redirect_stdout(printed):
            example = load_example()
            with example.pipeline as pipeline:
                with pipeline.create_flowdata() as flowdata:
                    flowdata.evidence.add("header.user-agent", CHROME)
                    flowdata.evidence.add("server.client-ip", CLIENT_IP)
                    flowdata.process()

        self.assertIn("Pipeline created with share usage element",
                      printed.getvalue())

        # The element has the settings in the example's 51d.json.
        with open(EXAMPLE.with_name("51d.json"), encoding="utf-8") as file:
            settings = json.load(file)["PipelineOptions"]["Elements"][0][
                "elementParameters"]
        usage = example.pipeline.get_element("shareusage")
        self.assertIsInstance(usage, ShareUsage)
        self.assertEqual(
            settings["requested_package_size"], usage.requested_package_size)
        self.assertEqual(settings["interval"], usage.interval)
        self.assertEqual(settings["share_percentage"], usage.share_percentage)

        # Closing the pipeline sends what is queued, which is the one
        # request processed.
        self.assertEqual(1, len(messages))
        message = messages[0]
        self.assertEqual(DEFAULT_ENDPOINT, message["url"])
        self.assertIsNot(False, message["options"].get("verify", True))
        self.assertEqual(1, message["body"].count("<Device>"))
        self.assertIn(f'<header Name="user-agent">{CHROME}</header>',
                      message["body"])
        self.assertIn(f"<ClientIP>{CLIENT_IP}</ClientIP>", message["body"])


if __name__ == "__main__":
    unittest.main()

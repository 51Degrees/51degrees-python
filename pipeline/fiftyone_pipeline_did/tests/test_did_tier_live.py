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

"""What a key on the Basic tier is entitled to, asked of the live cloud.

A Basic key carries the FODid product, so it gets a 51Did for the
non-marketing usage. It does not carry the CloudV5FODiD product, so the
service refuses it the standard and personalized usages and says which
product is missing. The key is read from ``_51DEGREES_RESOURCE_KEY_BASIC``
only, because these tests assert what that one tier gets, and they fail
when it is not set.
"""

import json
import urllib.parse
import urllib.request
import unittest

import pytest

from fiftyone_pipeline_did import DidClient, FodId, Usage
from fiftyone_pipeline_did.did_client import USER_AGENT

from .live_cloud import answered_without, find_resource_key, no_resource_key

pytestmark = [pytest.mark.live, pytest.mark.tier]

BASIC_KEY_NAMES = ("_51DEGREES_RESOURCE_KEY_BASIC",)
BASIC_KEY = find_resource_key(BASIC_KEY_NAMES)

FIELDS = ("idprobglobal", "idproblic")


class BasicTierLiveTests(unittest.TestCase):

    def setUp(self):
        if not BASIC_KEY:
            self.fail(no_resource_key(
                "the FODid product on the Basic tier",
                "a 51Did under each id.usage, expecting the marketing "
                "usages to be refused", several=True,
                names=BASIC_KEY_NAMES))
        self.endpoint = DidClient(BASIC_KEY).endpoint

    def fodid_for(self, usage):
        """The ``fodid`` member of the ``json`` endpoint's answer for the
        usage."""
        url = "{0}{1}.json?{2}".format(
            self.endpoint, urllib.parse.quote(BASIC_KEY, safe=""),
            urllib.parse.urlencode([
                ("id.usage", usage),
                ("values", "FODiD.IdProbGlobal"),
                ("values", "FODiD.IdProbLic")]))
        request = urllib.request.Request(
            url, data=b"", headers={"User-Agent": USER_AGENT},
            method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("fodid") or {}

    def test_non_marketing_usage_gets_a_51did(self):
        fodid = self.fodid_for("non-marketing")
        for field in FIELDS:
            if not fodid.get(field):
                self.fail(answered_without(
                    field + " for id.usage=non-marketing",
                    fodid.get(field + "nullreason"), "the FODid product"))
            self.assertEqual(
                Usage.NON_MARKETING, FodId.from_base64(fodid[field]).usage,
                field)

    def test_marketing_usages_are_refused_naming_the_product(self):
        for usage in ("standard", "personalized"):
            fodid = self.fodid_for(usage)
            for field in FIELDS:
                self.assertFalse(
                    fodid.get(field),
                    "A Basic key got {0} for id.usage={1}, which only a key "
                    "that carries the CloudV5FODiD product should get. Check "
                    "the key is still on the Basic tier.".format(
                        field, usage))
                name = "IdProbGlobal" if field == "idprobglobal" \
                    else "IdProbLic"
                self.assertEqual(
                    "Can not form {0}. For marketing (personalized or "
                    "standard) usages a CloudV5FODiD product needs to be a "
                    "part of the license.".format(name),
                    fodid.get(field + "nullreason"),
                    "the reason given for {0} with id.usage={1}".format(
                        field, usage))


if __name__ == "__main__":
    unittest.main()

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

"""The basic list filter accepts the keys it was given, in any letters, and
nothing else. Its list attribute is read by other code, so it keeps holding
the keys in lower case, and the filter matches what the list holds when the
list is set after the filter is made."""

import unittest

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter


class SetsItsOwnList(BasicListEvidenceKeyFilter):
    """A filter that sets its list without calling the base constructor."""

    def __init__(self):
        self.list = ["header.user-agent"]


class BasicListEvidenceKeyFilterTests(unittest.TestCase):

    def test_a_listed_key_is_accepted_in_any_letters(self):
        key_filter = BasicListEvidenceKeyFilter(
            ["Header.User-Agent", "query.sequence"])
        for key in ("header.user-agent", "HEADER.USER-AGENT",
                    "Header.User-Agent", "query.sequence", "Query.Sequence"):
            self.assertTrue(key_filter.filter_evidence_key(key), key)

    def test_a_key_that_is_not_listed_is_refused(self):
        key_filter = BasicListEvidenceKeyFilter(["header.user-agent"])
        for key in ("header.user", "header.user-agent2", "user-agent",
                    "cookie.user-agent", ""):
            self.assertFalse(key_filter.filter_evidence_key(key), key)

    def test_an_empty_list_accepts_nothing(self):
        key_filter = BasicListEvidenceKeyFilter([])
        self.assertFalse(key_filter.filter_evidence_key("header.user-agent"))
        self.assertFalse(key_filter.filter_evidence_key(""))

    def test_filtering_keeps_listed_keys_as_they_were_given(self):
        key_filter = BasicListEvidenceKeyFilter(["header.user-agent"])
        self.assertEqual(
            {"Header.User-Agent": "a browser"},
            key_filter.filter_evidence({
                "Header.User-Agent": "a browser",
                "header.accept": "text/html"}))

    def test_the_list_holds_the_keys_in_lower_case_in_order(self):
        key_filter = BasicListEvidenceKeyFilter(
            ["Query.Sequence", "header.user-agent", "Header.Host"])
        self.assertEqual(
            ["query.sequence", "header.user-agent", "header.host"],
            key_filter.list)
        self.assertIsInstance(key_filter.list, list)

    def test_a_list_set_after_the_filter_is_made_is_matched(self):
        key_filter = BasicListEvidenceKeyFilter(["header.user-agent"])
        key_filter.list = ["header.accept"]
        self.assertTrue(key_filter.filter_evidence_key("Header.Accept"))
        self.assertFalse(key_filter.filter_evidence_key("header.user-agent"))

    def test_a_subclass_that_sets_its_own_list_is_matched(self):
        key_filter = SetsItsOwnList()
        self.assertTrue(key_filter.filter_evidence_key("Header.User-Agent"))
        self.assertFalse(key_filter.filter_evidence_key("header.accept"))
        self.assertEqual(["header.user-agent"], key_filter.list)


if __name__ == "__main__":
    unittest.main()

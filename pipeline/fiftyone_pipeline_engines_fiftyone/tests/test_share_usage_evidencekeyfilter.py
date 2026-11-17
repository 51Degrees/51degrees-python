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

import unittest

from fiftyone_pipeline_engines_fiftyone.share_usage_evidencekeyfilter import \
    ShareUsageEvidenceKeyFilter


class ShareUsageEvidenceKeyFilterTests(unittest.TestCase):

    def test_default_rules(self):
        """!
        Check that by default headers other than Cookie are shared, cookies,
        session values and query string parameters only when their names
        start with 51D_, and any other evidence.
        """

        keys = ShareUsageEvidenceKeyFilter()

        self.assertTrue(keys.filter_evidence_key("header.user-agent"))
        self.assertFalse(keys.filter_evidence_key("header.cookie"))
        self.assertTrue(keys.filter_evidence_key("cookie.51d_screenpixelswidth"))
        self.assertTrue(keys.filter_evidence_key("cookie.51D_ScreenPixelsWidth"))
        self.assertFalse(keys.filter_evidence_key("cookie.sessionid"))
        self.assertFalse(keys.filter_evidence_key("cookie.a.b"))
        self.assertTrue(keys.filter_evidence_key("session.51d_value"))
        self.assertFalse(keys.filter_evidence_key("session.org.example.attribute"))
        self.assertTrue(keys.filter_evidence_key("query.51d_gethighentropyvalues"))
        self.assertFalse(keys.filter_evidence_key("query.password"))
        self.assertFalse(keys.filter_evidence_key("query.id.email"))
        self.assertTrue(keys.filter_evidence_key("server.client-ip"))
        self.assertTrue(keys.filter_evidence_key("nodot"))

    def test_field_is_everything_after_the_first_dot(self):
        """!
        Check that a name containing a dot is matched as a whole against
        the parameters to share.
        """

        keys = ShareUsageEvidenceKeyFilter(query_whitelist=["valid.email"])

        self.assertTrue(keys.filter_evidence_key("query.valid.email"))
        self.assertFalse(keys.filter_evidence_key("query.valid"))
        self.assertFalse(keys.filter_evidence_key("query.other.name"))

    def test_lists_ignore_case(self):
        """!
        Check that the headers not to share and the parameters to share
        are matched without regard to case.
        """

        keys = ShareUsageEvidenceKeyFilter(
            query_whitelist=["Campaign"],
            header_blacklist=["X-Secret"])

        self.assertFalse(keys.filter_evidence_key("header.x-secret"))
        self.assertTrue(keys.filter_evidence_key("query.campaign"))
        self.assertTrue(keys.filter_evidence_key("header.user-agent"))

    def test_lists_from_comma_separated_strings(self):
        """!
        Check that a string given for either list, the form a
        configuration file gives a list in, is read as names separated by
        commas, each trimmed.
        """

        keys = ShareUsageEvidenceKeyFilter(
            query_whitelist="Campaign, utm_source",
            header_blacklist="X-Secret,X-Other")

        self.assertTrue(keys.filter_evidence_key("query.campaign"))
        self.assertTrue(keys.filter_evidence_key("query.utm_source"))
        self.assertFalse(keys.filter_evidence_key("query.c"))
        self.assertFalse(keys.filter_evidence_key("header.x-secret"))
        self.assertFalse(keys.filter_evidence_key("header.x-other"))
        self.assertTrue(keys.filter_evidence_key("header.x"))

    def test_no_parameter_list_shares_every_parameter(self):
        """!
        Check that None in place of the parameters to share shares every
        parameter, and an empty list only those starting 51D_.
        """

        every = ShareUsageEvidenceKeyFilter(query_whitelist=None)
        prefixed = ShareUsageEvidenceKeyFilter(query_whitelist=[])

        self.assertTrue(every.filter_evidence_key("query.campaign"))
        self.assertFalse(prefixed.filter_evidence_key("query.campaign"))
        self.assertTrue(prefixed.filter_evidence_key("query.51d_campaign"))

    def test_the_option_given_decides_whatever_the_list(self):
        """!
        Check that with share_all_query_string_parameters given, None in
        place of the parameters to share holds no names, as an empty list
        does, so the option off shares only parameters starting 51D_ and
        the option on shares every parameter.
        """

        for query_whitelist in (None, []):
            prefixed = ShareUsageEvidenceKeyFilter(
                query_whitelist=query_whitelist,
                share_all_query_string_parameters=False)
            every = ShareUsageEvidenceKeyFilter(
                query_whitelist=query_whitelist,
                share_all_query_string_parameters=True)

            self.assertFalse(prefixed.filter_evidence_key("query.campaign"))
            self.assertTrue(
                prefixed.filter_evidence_key("query.51d_campaign"))
            self.assertTrue(every.filter_evidence_key("query.campaign"))

    def test_session_cookie(self):
        """!
        Check that the session cookie is included only when asked for, and
        that no other ordinary cookie is.
        """

        kept = ShareUsageEvidenceKeyFilter(cookie="SessionId", include_session=True)
        sent = ShareUsageEvidenceKeyFilter(cookie="SessionId")

        self.assertTrue(kept.filter_evidence_key("cookie.sessionid"))
        self.assertFalse(sent.filter_evidence_key("cookie.sessionid"))
        self.assertFalse(kept.filter_evidence_key("cookie._ga"))
        self.assertFalse(sent.filter_evidence_key("cookie._ga"))

    def test_share_all(self):
        """!
        Check that sharing everything shares the evidence the other rules
        leave out, apart from the evidence that is never shared and the
        cookies that do not start 51D_.
        """

        keys = ShareUsageEvidenceKeyFilter(share_all=True)

        self.assertFalse(keys.filter_evidence_key("header.cookie"))
        self.assertFalse(keys.filter_evidence_key("cookie.sessionid"))
        self.assertTrue(
            keys.filter_evidence_key("cookie.51D_screenpixelswidth"))
        self.assertTrue(keys.filter_evidence_key("query.password"))
        self.assertTrue(keys.filter_evidence_key("query.id.usage"))
        self.assertTrue(keys.filter_evidence_key("server.request-method"))
        self.assertFalse(keys.filter_evidence_key("query.id.email"))
        self.assertFalse(keys.filter_evidence_key("header.id.email"))
        self.assertFalse(keys.filter_evidence_key("query.id.salt"))
        self.assertFalse(keys.filter_evidence_key("header.id.salt"))
        self.assertFalse(keys.filter_evidence_key("server.request-query"))
        self.assertFalse(keys.filter_evidence_key("server.request-path"))

    def test_every_query_parameter_when_sharing_them_all(self):
        """!
        Check that sharing every query string parameter shares one not on
        the list, and that a filter made without it keeps to the list.
        """

        every = ShareUsageEvidenceKeyFilter(
            query_whitelist=["campaign"],
            share_all_query_string_parameters=True)
        listed = ShareUsageEvidenceKeyFilter(query_whitelist=["campaign"])

        self.assertTrue(every.filter_evidence_key("query.password"))
        self.assertFalse(listed.filter_evidence_key("query.password"))
        self.assertTrue(listed.filter_evidence_key("query.campaign"))

    def test_the_session_cookie_is_kept_for_the_tracker_alone(self):
        """!
        Check that, when all evidence is shared, the session cookie is kept
        by the tracker's filter and by no other.
        """

        kept = ShareUsageEvidenceKeyFilter(
            cookie="SessionId", include_session=True, share_all=True)
        sent = ShareUsageEvidenceKeyFilter(cookie="SessionId", share_all=True)

        self.assertTrue(kept.filter_evidence_key("cookie.sessionid"))
        self.assertFalse(sent.filter_evidence_key("cookie.sessionid"))
        self.assertFalse(kept.filter_evidence_key("cookie._ga"))

    def test_never_shared_in_every_mode(self):
        """!
        Check that the email address, the salt for hashed email
        identifiers, the query string, the path and the Cookie header are
        never shared, whether bare or after a prefix, and without regard to
        case.
        """

        for keys in (
                ShareUsageEvidenceKeyFilter(),
                ShareUsageEvidenceKeyFilter(query_whitelist=None),
                ShareUsageEvidenceKeyFilter(share_all=True)):
            for key in (
                    "id.email", "id.salt",
                    "query.id.email", "QUERY.ID.EMAIL",
                    "header.id.salt", "HEADER.ID.SALT",
                    "server.request-query", "SERVER.REQUEST-QUERY",
                    "server.request-path", "SERVER.REQUEST-PATH",
                    "header.cookie", "HEADER.COOKIE"):
                self.assertFalse(keys.filter_evidence_key(key), key)

    def test_never_shared_keys_match_whole_parts(self):
        """!
        Check that a key that only ends with the same letters as a key
        never shared is treated as an ordinary key.
        """

        keys = ShareUsageEvidenceKeyFilter(query_whitelist=["valid.email"])

        self.assertTrue(keys.filter_evidence_key("query.valid.email"))
        self.assertTrue(
            ShareUsageEvidenceKeyFilter(share_all=True)
                .filter_evidence_key("query.valid.email"))

    def test_naming_a_parameter_does_not_share_the_query_string(self):
        """!
        Check that sharing one parameter does not share the whole query
        string, which carries every parameter.
        """

        keys = ShareUsageEvidenceKeyFilter(query_whitelist=["utm_source"])

        self.assertTrue(keys.filter_evidence_key("query.utm_source"))
        self.assertFalse(keys.filter_evidence_key("server.request-query"))

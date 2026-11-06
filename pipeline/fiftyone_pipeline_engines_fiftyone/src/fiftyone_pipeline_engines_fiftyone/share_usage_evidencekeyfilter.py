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

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter

# Cookies, session values and query string parameters whose names start with
# this are the ones 51Degrees sets, and are shared.
FIFTYONE_PREFIX = "51d_"

# The Cookie header carries every cookie, including the ones the cookie rule
# leaves out, so it is not shared unless all evidence is.
BLOCKED_HEADERS = ("cookie",)

# Evidence that is never shared, whatever the settings, matched as the whole
# key or after a '.'. 'id.email' and 'id.salt' are a raw email address and the
# salt used to make hashed email identifiers. 'request-query' is the whole query
# string, which would undo the rules for its parameters. 'request-path' would
# make each page a visitor opens look like a new session to the tracker.
NEVER_SHARED_KEYS = ("id.email", "id.salt", "request-query", "request-path")

class ShareUsageEvidenceKeyFilter(BasicListEvidenceKeyFilter):
    """
    The ShareUsageEvidenceKeyFilter decides which evidence the 51Degrees
    ShareUsage service is sent. Headers are shared unless they are blocked,
    cookies and session values only when their names start with 51D_, and
    query string and form parameters only when their names start with 51D_ or
    are on the list to share. Any other evidence is shared.
    """

    def __init__(
            self,
            cookie = None,
            query_whitelist = (),
            header_blacklist = (),
            include_session = False,
            share_all = False):
        """!
        Constructor for ShareUsageEvidenceKeyFilter
        @type cookie: string
        @param cookie: the name of the cookie that identifies the session
        @type query_whitelist: list
        @param query_whitelist: query string and form parameters to share as
        well as those starting 51D_, or None to share every parameter
        @type header_blacklist: list
        @param header_blacklist: headers not to share
        @type include_session: bool
        @param include_session: whether the session cookie is included
        @type share_all: bool
        @param share_all: whether all evidence is shared, apart from the
        evidence that is never shared
        """
        self.cookie = cookie.lower() if cookie else None

        self.query_whitelist = None if query_whitelist is None else \
            [parameter.lower() for parameter in query_whitelist]

        self.header_blacklist = \
            [header.lower() for header in header_blacklist or ()]

        self.include_session = include_session

        self.share_all = share_all

    def filter_evidence_key(self, key):

        """!
        Check if a specific key should be filtered.

        @type key: string
        @param key: to check in the filter

        @rtype: bool
        @return: Is this key in the filter's keys list?

        """
        key = key.lower()

        if any(key == never_shared or key.endswith("." + never_shared)
                for never_shared in NEVER_SHARED_KEYS):
            return False

        if self.share_all:
            return True

        # The prefix is everything before the first dot and the field
        # everything after it, so a field can itself contain dots.
        prefix, separator, field = key.partition(".")

        if not separator:
            return True
        elif prefix == "header":
            # Add the header to the list if the header name does not
            # appear in the list of blocked headers
            return field not in self.header_blacklist and \
                field not in BLOCKED_HEADERS
        elif prefix == "cookie":
            # Only add cookies that start with the 51Degrees cookie
            # prefix
            return field.startswith(FIFTYONE_PREFIX) or \
                (self.include_session and field == self.cookie)
        elif prefix == "session":
            # Only session values that start with the 51Degrees
            # cookie prefix
            return field.startswith(FIFTYONE_PREFIX)
        elif prefix == "query":
            # If no query string parameter list was given then share all
            # of them. Otherwise, only include query string parameters
            # that start with 51d_ or that are in the list.
            return self.query_whitelist is None or \
                field.startswith(FIFTYONE_PREFIX) or \
                field in self.query_whitelist
        else:
            # Add anything that is not a cookie, header, session
            # variable or query parameter
            return True

class ShareUsageTrackerEvidenceKeyFilter(ShareUsageEvidenceKeyFilter):
    """
    The evidence the ShareUsageTracker compares to decide whether a request
    repeats one already shared. The session id and sequence number are left
    out, because they make every request different.
    """

    def filter_evidence_key(self, key):

        if key.lower() in ("query.session-id", "query.sequence"):
            return False

        return super(ShareUsageTrackerEvidenceKeyFilter, self)\
            .filter_evidence_key(key)

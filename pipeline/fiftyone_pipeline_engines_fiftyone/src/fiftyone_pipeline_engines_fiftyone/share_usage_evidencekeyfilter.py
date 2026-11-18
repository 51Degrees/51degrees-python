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
from fiftyone_pipeline_core.javascriptbuilder import JavascriptBuilderElement

# Cookies, session values and query string parameters whose names start with
# this are the ones 51Degrees sets, and are shared.
FIFTYONE_PREFIX = "51d_"

# Evidence that is never shared, whatever the settings, matched as the whole
# key or after a '.'. 'id.email' and 'id.salt' are a raw email address and the
# salt used to make hashed email identifiers. 'request-query' is the whole query
# string, which would undo the rules for its parameters. 'request-path' would
# make each page a visitor opens look like a new session to the tracker.
# 'header.cookie' is the Cookie header, which carries every cookie, and the
# cookies that are shared are shared as their own 'cookie.' evidence.
NEVER_SHARED_KEYS = (
    "id.email", "id.salt", "request-query", "request-path", "header.cookie")


# The query string parameters the JavaScript Builder's specification lists as
# its accepted Evidence. Its filter also passes every other parameter, only so
# that it can send them back to the callback.
JAVASCRIPT_BUILDER_PARAMETERS = (
    "query.fod-js-object-name", "query.fod-js-enable-cookies")


def _used_by(pipeline, key):
    """!
    Whether a FlowElement of the Pipeline accepts the key as evidence. The
    JavaScript Builder is asked only about the parameters its specification
    says it accepts.
    """
    if pipeline is None:
        return False
    for element in pipeline.flow_elements:
        if isinstance(element, JavascriptBuilderElement):
            if key.lower() in JAVASCRIPT_BUILDER_PARAMETERS:
                return True
        elif element.get_evidence_key_filter().filter_evidence_key(key):
            return True
    return False


def _split_names(names):
    """!
    A configuration file gives a list of names as one comma-separated
    string, so a string is split on commas into its names, each trimmed,
    with empty entries left out. Any other value, such as a list or None, is
    returned as it is.
    """
    if isinstance(names, str):
        return [name.strip() for name in names.split(",") if name.strip()]
    return names


class ShareUsageEvidenceKeyFilter(BasicListEvidenceKeyFilter):
    """
    The ShareUsageEvidenceKeyFilter decides which evidence the 51Degrees
    ShareUsage service is sent. Cookies are shared only when their names
    start with 51D_, and query string and form parameters only when their
    names start with 51D_ or the Pipeline uses them as evidence, whatever
    the other settings. Headers are shared unless they are blocked, and
    session values only when their names start with 51D_. Any other
    evidence is shared.
    """

    def __init__(
            self,
            cookie = None,
            query_whitelist = (),
            header_blacklist = (),
            include_session = False,
            share_all = False,
            share_all_query_string_parameters = False):
        """!
        Constructor for ShareUsageEvidenceKeyFilter
        @type cookie: string
        @param cookie: the name of the cookie that identifies the session
        @type query_whitelist: list or str
        @param query_whitelist: deprecated, and has no effect. A query
        string or form parameter is shared only when its name starts with
        51D_ or the Pipeline uses it as evidence.
        @type header_blacklist: list or str
        @param header_blacklist: headers not to share. A string is read as
        names separated by commas.
        @type include_session: bool
        @param include_session: whether the session cookie is included
        @type share_all: bool
        @param share_all: whether all evidence is shared, apart from the
        evidence that is never shared and cookies not starting 51D_
        @type share_all_query_string_parameters: bool
        @param share_all_query_string_parameters: deprecated, and has no
        effect, as query_whitelist.
        """
        self.cookie = cookie.lower() if cookie else None

        query_whitelist = _split_names(query_whitelist)
        header_blacklist = _split_names(header_blacklist)

        # Kept so that code reading them still works. Neither decides what
        # is shared.
        self.query_whitelist = \
            [parameter.lower() for parameter in query_whitelist or ()]

        self.header_blacklist = \
            [header.lower() for header in header_blacklist or ()]

        self.include_session = include_session

        self.share_all = share_all

        self.share_all_query_string_parameters = \
            share_all_query_string_parameters

    def filter_evidence(self, evidence_key_object, pipeline=None):

        """!
        The evidence to share, from a dictionary of evidence.

        @type evidence_key_object: dict
        @param evidence_key_object: evidence keys and values
        @type pipeline: Pipeline
        @param pipeline: the Pipeline the evidence came to, whose evidence
        decides which query string and form parameters are shared
        @rtype: dict
        @return: the evidence to share
        """

        return {key: value for key, value in evidence_key_object.items()
                if self.filter_evidence_key(key, pipeline)}

    def filter_evidence_key(self, key, pipeline=None):

        """!
        Check if a specific key should be filtered.

        @type key: string
        @param key: to check in the filter
        @type pipeline: Pipeline
        @param pipeline: the Pipeline the evidence came to. Without one, a
        query string or form parameter is shared only when its name starts
        with 51D_.

        @rtype: bool
        @return: Is this key in the filter's keys list?

        """
        original = key
        key = key.lower()

        if any(key == never_shared or key.endswith("." + never_shared)
                for never_shared in NEVER_SHARED_KEYS):
            return False

        # The prefix is everything before the first dot and the field
        # everything after it, so a field can itself contain dots.
        prefix, separator, field = key.partition(".")

        # A cookie a site sets for itself is never shared, even when all
        # evidence is. The tracker alone keeps the session cookie.
        if separator and prefix == "cookie":
            return field.startswith(FIFTYONE_PREFIX) or \
                (self.include_session and field == self.cookie)

        # A query string or form parameter is shared only when 51Degrees set
        # it or the Pipeline uses it as evidence, even when all evidence is,
        # so that a value such as a password is never sent.
        if separator and prefix == "query":
            return field.startswith(FIFTYONE_PREFIX) or \
                _used_by(pipeline, original)

        if self.share_all:
            return True

        if not separator:
            return True
        elif prefix == "header":
            # Add the header to the list if the header name does not
            # appear in the list of blocked headers
            return field not in self.header_blacklist
        elif prefix == "session":
            # Only session values that start with the 51Degrees
            # cookie prefix
            return field.startswith(FIFTYONE_PREFIX)
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

    def filter_evidence_key(self, key, pipeline=None):

        if key.lower() in ("query.session-id", "query.sequence"):
            return False

        return super(ShareUsageTrackerEvidenceKeyFilter, self)\
            .filter_evidence_key(key, pipeline)

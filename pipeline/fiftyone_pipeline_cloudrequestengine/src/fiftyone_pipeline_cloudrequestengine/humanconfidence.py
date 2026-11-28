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

"""!
Human Confidence that reaches the publisher's server sealed.

Where a page runs the 51Degrees browser tests, HumanConfidence reaches the
server as a sealed result the browser can't read. The page sends it back as
the parameter humanconfidence, which becomes the evidence
query.humanconfidence. The Cloud Request Engine then redeems it through its
one JSON call, with a transaction this package issued for the page and kept
on the server, and DerivedCloud gives the two properties a consumer reads,
HumanConfidence and HumanConfidenceSource. A consumer never redeems a sealed
result itself.

See the Human Confidence page of the pipeline specification:
https://github.com/51Degrees/specifications/blob/main/pipeline-specification/features/human-confidence.md
"""

import json
import secrets
import threading
import time
import urllib.parse
from collections import OrderedDict

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

from .clouddata import CloudData
from .cloudengine import CloudEngine

# The evidence that carries the sealed result, exactly as it arrived.
SEALED_RESULT_EVIDENCE = "query.humanconfidence"

# The name the sealed result is sent under, once its prefix is removed.
SEALED_RESULT_NAME = "humanconfidence"

# The evidence that names the page the sealed result came from, being the
# id of the HumanConfidencePage the server gave that page. It is only a
# handle: the transaction itself is never taken from the request.
PAGE_EVIDENCE = "query.humanconfidencepage"

# The name the JSON call sends the kept transaction under.
TRANSACTION_PARAMETER = "transaction"

# Evidence whose key strips to one of these is left out of a call that
# redeems, so the kept transaction is the only one. challenge is the older
# name of the same value.
TRANSACTION_SUFFIXES = frozenset(("transaction", "challenge"))

# The property the JSON call must ask for to get the redeemed value.
HUMAN_CONFIDENCE_PROPERTY = "derived.humanconfidence"

# The values a redeemed sealed result gives.
REDEEMED_VALUES = ("High", "Medium", "Low")

# HumanConfidence for a sealed result that was not redeemed, because Human
# Confidence can't be worked out from it.
NOT_REDEEMED_VALUE = "Medium"

# HumanConfidenceSource on every request that carries a sealed result.
ACTIVE = "Active"


def evidence_name(key):
    """!
    The name of an evidence key without its prefix, in lower case.
    """

    key = str(key)
    return key.partition(".")[2].lower() if "." in key else key.lower()


def evidence_value(evidence, key):
    """!
    The value of the evidence key given, compared without regard to case,
    whether an element accepted it or not, or None where there is none.

    @param evidence: a FlowData's Evidence
    @param key: the evidence key, with its prefix
    """

    key = key.lower()
    # An older fiftyone_pipeline_core sets nothing aside.
    unaccepted = getattr(evidence, "get_unaccepted", dict)()
    for source in (evidence.get_all(), unaccepted):
        for name, value in source.items():
            if str(name).lower() == key:
                return value
    return None


def sealed_result_of(evidence):
    """!
    The sealed result a request carries, or None where its evidence holds
    no query.humanconfidence, or one that is empty.
    """

    value = evidence_value(evidence, SEALED_RESULT_EVIDENCE)
    if value is None:
        return None
    value = str(value)
    return value if value != "" else None


class HumanConfidencePage(object):

    """!
    What a page that asks for Human Confidence needs, from
    HumanConfidenceTransactions.issue. The page loads the 51Degrees client
    script from script_url, which carries the page's transaction, and sends
    id back as the parameter humanconfidencepage beside the sealed result.
    """

    def __init__(self, page_id, transaction):
        self.id = page_id
        self._transaction = transaction

    def script_url(self, cloud_endpoint, resource_key):
        """!
        The address of the 51Degrees client script for this page, which
        binds the sealed result the page gets to the page's transaction.

        @param cloud_endpoint: the cloud API base, ending in /api/v4/
        @param resource_key: the Resource Key of the page
        """

        base = cloud_endpoint if cloud_endpoint.endswith("/") \
            else cloud_endpoint + "/"
        return (base + urllib.parse.quote(resource_key, safe="") + ".js?"
                + urllib.parse.urlencode(
                    {TRANSACTION_PARAMETER: self._transaction}))

    def __repr__(self):
        # The transaction is left out, so a log of the page never holds it.
        return "HumanConfidencePage(id={!r})".format(self.id)


class HumanConfidenceTransactions(object):

    """!
    Issues a new transaction for each page and keeps it on the server, so a
    sealed result redeems only for the page it was made for. Each
    transaction is used once. One that is not used within lifetime_seconds,
    or that is pushed out by more than capacity newer pages, is dropped, and
    a sealed result from that page is then not redeemed.

    The transactions are kept in this process. A server run as several
    processes needs each request for a page to reach the process that
    served the page.

    The only public method is issue. A consumer has no way to get a
    transaction back, as the specification asks: only the Cloud Request
    Engine takes one, through _take, when it redeems. A store that keeps
    transactions elsewhere is a subclass that overrides issue and _take.
    """

    def __init__(self, lifetime_seconds=600, capacity=10000):
        self.lifetime_seconds = lifetime_seconds
        self.capacity = capacity
        self._kept = OrderedDict()
        self._lock = threading.Lock()

    def issue(self):
        """!
        A new transaction for one page, kept here.

        @rtype: HumanConfidencePage
        """

        page = HumanConfidencePage(
            secrets.token_urlsafe(18), secrets.token_urlsafe(18))
        now = time.monotonic()
        with self._lock:
            self._drop_old(now)
            self._kept[page.id] = (page._transaction,
                                   now + self.lifetime_seconds)
            while len(self._kept) > self.capacity:
                self._kept.popitem(last=False)
        return page

    def _take(self, page_id):
        """!
        The transaction kept for the page named, which is then forgotten so
        it is used once, or None where none is kept for it. For the Cloud
        Request Engine only, so it isn't part of the public surface.
        """

        if not isinstance(page_id, str) or page_id == "":
            return None
        now = time.monotonic()
        with self._lock:
            self._drop_old(now)
            kept = self._kept.pop(page_id, None)
        return kept[0] if kept is not None else None

    def _drop_old(self, now):
        while self._kept:
            page_id, (_, expires) = next(iter(self._kept.items()))
            if expires > now:
                break
            del self._kept[page_id]


class DerivedCloud(CloudEngine):

    """!
    The derived properties, read from the "derived" section of the cloud
    response and available as flowdata.derived, being HumanConfidence and
    HumanConfidenceSource among them.

    On a request that carries a sealed result, HumanConfidenceSource is
    Active, and HumanConfidence is the value the Cloud Request Engine
    redeemed, or Medium wherever the sealed result was not redeemed. A read
    of either never raises for that, and this engine adds no error of its
    own. On any other request this engine reads the section as every cloud
    engine does.
    """

    DATA_KEY = "derived"

    def __init__(self):

        super(DerivedCloud, self).__init__()

        self.datakey = self.DATA_KEY

    def process_internal(self, flowdata):

        if sealed_result_of(flowdata.evidence) is None:
            super(DerivedCloud, self).process_internal(flowdata)
            return

        try:
            super(DerivedCloud, self).process_internal(flowdata)
            data = flowdata.get(self.datakey)
        except Exception:
            # The Cloud Request Engine made no request, or its request
            # failed and is already recorded as its error.
            data = CloudData(self, {})
            flowdata.set_element_data(data)

        data.contents["humanconfidence"] = AspectPropertyValue(
            value=self._redeemed_value(flowdata) or NOT_REDEEMED_VALUE)
        data.contents["humanconfidencesource"] = AspectPropertyValue(
            value=ACTIVE)

    def _redeemed_value(self, flowdata):
        """!
        The value the Cloud Request Engine redeemed, or None where it did
        not redeem the sealed result or the response holds no High, Medium
        or Low for it.
        """

        try:
            request_data = flowdata.get(self._request_engine.datakey)
        except Exception:
            return None
        if not vars(request_data).get("_human_confidence_redeemed", False):
            return None
        try:
            answer = json.loads(self._cloud_response(flowdata))
        except Exception:
            return None
        derived = answer.get(self.datakey) if isinstance(answer, dict) \
            else None
        value = derived.get("humanconfidence") \
            if isinstance(derived, dict) else None
        return value if value in REDEEMED_VALUES else None

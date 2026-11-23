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
Redeeming a sealed Human Confidence level, as the Human Confidence page of
the specification sets out:
https://github.com/51Degrees/specifications/blob/main/pipeline-specification/features/human-confidence.md

The names the page and the cloud service use are kept together here, in
HumanConfidenceNames, so each is stated once.
"""

import secrets
import threading
import time
from collections import OrderedDict


class HumanConfidenceNames:

    """!
    The names used to redeem a sealed Human Confidence level.
    """

    # The evidence that carries the sealed value, and the name the cloud
    # service reads it under in the JSON call.
    SEALED_EVIDENCE = "query.humanconfidence"
    SEALED_PARAMETER = "humanconfidence"

    # The name the challenge is sent under, to the cloud service by the
    # page and by the engine. It is the name a sealed 51Did creator context
    # result uses.
    CHALLENGE_PARAMETER = "challenge"

    # The name the page sends its page value under, with the sealed value,
    # so the engine can find the challenge it kept for that page. The
    # engine never sends it to the cloud service.
    PAGE_PARAMETER = "humanconfidencepage"
    PAGE_EVIDENCE = "query." + PAGE_PARAMETER

    # The requested property the JSON call names on a request that carries
    # a sealed value, as the engine writes property names.
    REQUESTED_PROPERTY = "derived.humanconfidence"

    # The section and members of the answer that hold the two properties.
    SECTION = "derived"
    LEVEL = "humanconfidence"
    SOURCE = "humanconfidencesource"

    # The levels a sealed value redeems for, the source of a sealed level,
    # and the level given when the sealed value is not redeemed.
    LEVELS = ("High", "Medium", "Low")
    ACTIVE = "Active"
    NOT_REDEEMED = "Low"


class HumanConfidenceChallenges:

    """!
    The challenges the engine has given to pages and not yet used. Each
    page gets a new challenge, kept here on the server under a page value,
    and the challenge is used once, when the sealed value the page sends
    back is redeemed. A challenge that is not used within lifetime_seconds
    is dropped.

    One instance serves one process. Where several servers answer the same
    site, give each engine an object with the same issue and take methods
    that keeps the challenges where every server can reach them.
    """

    # Long enough for the browser tests to run and the page to send the
    # sealed value back, which takes a few seconds.
    DEFAULT_LIFETIME_SECONDS = 60

    # The most challenges kept at once. The oldest is dropped first.
    DEFAULT_CAPACITY = 100000

    def __init__(self, lifetime_seconds=DEFAULT_LIFETIME_SECONDS,
                 capacity=DEFAULT_CAPACITY, clock=time.monotonic):

        """!
        @type lifetime_seconds: float
        @param lifetime_seconds: how long a challenge is kept
        @type capacity: int
        @param capacity: the most challenges kept at once
        @type clock: callable
        @param clock: gives the time in seconds, for tests
        """

        self._lifetime = lifetime_seconds
        self._capacity = capacity
        self._clock = clock
        self._lock = threading.Lock()
        # Page value to (challenge, time issued), oldest first.
        self._kept = OrderedDict()

    def issue(self):

        """!
        A new page value and challenge for one page, keeping the challenge.

        @rtype: tuple
        @return: the page value and the challenge
        """

        page = secrets.token_hex(16)
        challenge = secrets.token_hex(16)
        now = self._clock()
        with self._lock:
            self._drop_expired(now)
            while len(self._kept) >= self._capacity:
                self._kept.popitem(last=False)
            self._kept[page] = (challenge, now)
        return page, challenge

    def take(self, page):

        """!
        The challenge kept for a page value, which is then no longer kept,
        or None where there is none or it has been kept too long.

        @type page: str
        @param page: the page value the page sent back
        @rtype: str
        @return: the challenge, or None
        """

        if not isinstance(page, str) or page == "":
            return None
        now = self._clock()
        with self._lock:
            self._drop_expired(now)
            kept = self._kept.pop(page, None)
        return None if kept is None else kept[0]

    def _drop_expired(self, now):
        while self._kept:
            page, (_, issued) = next(iter(self._kept.items()))
            if now - issued < self._lifetime:
                break
            del self._kept[page]

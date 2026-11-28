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

"""The 51Did cloud client.

:class:`DidClient` handles every manipulation of a 51Did a server needs
against the 51Degrees cloud, so server code never builds a cloud URL or
handles a key itself. It fetches the signing public keys and keeps them,
picks the key in force when an identifier was created, verifies a
signature offline against that key, verifies a signature through the
cloud's verify endpoint, and redeems a sealed creator context result with
the licence key, returning a typed :class:`RedeemResult`. The verify and
redeem calls also read the Human Confidence Value a 51Did carries, where
the cloud gives it.

Creating a 51Did is not part of this client. Creation is the cloud ``json``
endpoint through the cloud request engine and pipeline, and a page creates
from the browser because the identifier describes the browser's own
connection. The verify-context and verify-full endpoints are browser calls
for the same reason and are not offered here.

Every method that reaches the cloud is a coroutine, so a server awaits
it on its event loop and there is no blocking form. The default transport
runs the standard library's ``urllib`` on a worker thread through
:func:`asyncio.to_thread`, and a fully non-blocking transport built on
``aiohttp`` or ``httpx`` can be supplied instead.

Standard library only (``asyncio``, ``urllib`` and ``json``), so this
package gains no dependency the pipeline does not already carry.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
# Kept so that ``from ... import *`` of this module still gives it.
import threading
import urllib.error
import urllib.parse
import urllib.request
# Kept so that ``from ... import *`` of this module still gives it.
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
# Imported under a private name so that a star import of this module gives
# no name it did not give before.
from enum import EnumMeta as _EnumMeta
from typing import (
    Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union)

from ._owid import Version

# The layout is read through the private module rather than imported by
# name, so that this module's namespace offers none of it.
from . import _layout
from .fod_id import (
    DATE_EPOCH,
    FodId,
    _date_minutes,
    _deprecated_layout_name,
    _trim_white_space,
)
from .id_type import IdType

#: The layout names :func:`__getattr__` still gives, with a warning,
#: until they are removed.
_DEPRECATED_LAYOUT_NAMES = frozenset((
    "GUID_LENGTH",
    "HEADER_LENGTH",
    "MATCH_KEY_LENGTH",
))


def __getattr__(name: str) -> int:
    """Gives the deprecated layout names, with a warning."""
    return _deprecated_layout_name(__name__, _DEPRECATED_LAYOUT_NAMES, name)


#: The public cloud API base, used when neither the ``endpoint`` argument
#: nor the ``_51DEGREES_CLOUD_ENDPOINT`` environment variable is set.
DEFAULT_ENDPOINT = "https://cloud.51degrees.com/api/v4/"

#: The environment variable the cloud request engine reads for the API
#: base, honoured here when no endpoint argument is given.
CLOUD_ENDPOINT_VARIABLE = "_51DEGREES_CLOUD_ENDPOINT"

def _endpoint_from_environment() -> Optional[str]:
    """The API base :data:`CLOUD_ENDPOINT_VARIABLE` gives, or None when it is
    unset or empty.
    """
    return os.environ.get(CLOUD_ENDPOINT_VARIABLE) or None


_BOUNDARY_TOLERANCE = timedelta(minutes=15)

#: A cached key list older than this is fetched again, whole, before use.
#: A key may be replaced before its end, and the client picks up the
#: replacement on the first signature failure or at this refresh, so this
#: also bounds how long a replaced key is trusted offline.
KEY_LIST_MAX_AGE = timedelta(days=1)

# The shortest time between two fetches made for a date the keys held do
# not cover or for a signature that failed with every key held, a failed
# attempt included, so that a forged date or signature cannot make every
# lookup call the cloud. The first fetch and the daily refresh neither
# count toward it nor wait for it.
_REFETCH_INTERVAL = timedelta(minutes=1)

#: The only envelope version the cloud signs and verifies.
SUPPORTED_VERSION = Version.VERSION3

#: Seconds to wait for the cloud before the default transport gives up.
DEFAULT_TIMEOUT = 30.0

# The longest encoded identifier this client will look at. This is a guard
# against obviously malformed input, not a statement about how long a
# 51Did is, because the lengths an identifier can have belong to the
# cloud. The figure is arbitrary and generous on purpose so that nothing
# about the layout of an identifier can be read from it.
_MAXIMUM_ENCODED_LENGTH = 4096


def _package_version() -> str:
    """The installed version of this package, for the User-Agent, or
    ``unknown`` when it is imported from a checkout that is not
    installed."""
    try:
        from importlib.metadata import version
        return version("fiftyone_pipeline_did")
    except Exception:
        return "unknown"


#: Sent with every request so the cloud can tell which package called.
USER_AGENT = "fiftyone_pipeline_did/" + _package_version()

# The header the cloud reads a License Key from, used where a request has
# no form body to carry one, so the key never travels in a URL.
_LICENCE_HEADER = "X-51D-License-Key"

#: The reason given for no Human Confidence Value where an answer that
#: verified or redeemed a 51Did held neither ``humanConfidence`` nor
#: ``humanConfidenceNullReason``, as an answer from a cloud from before the
#: Value was added does.
NO_HUMAN_CONFIDENCE_REASON = (
    "The cloud did not return a Human Confidence Value. A cloud from "
    "before the Value was added returns none.")

# Marks a redeem argument that was not given, so that an explicit None
# still reads as it always has.
_NOT_GIVEN: Any = object()


#: The :class:`ContextResult` members that are obsolete, each with the
#: message the warning gives. What happened to the sealed result is now
#: read from :attr:`RedeemResult.status`. The cloud still writes the same
#: words to ``context``, so each member keeps its value and goes on
#: working.
_OBSOLETE_CONTEXT_MEMBERS = {
    "EXPIRED": "ContextResult.EXPIRED is obsolete. Use "
               "RedeemStatus.EXPIRED, read from RedeemResult.status.",
    "REPLAYED": "ContextResult.REPLAYED is obsolete. Use "
                "RedeemStatus.REPLAYED, read from RedeemResult.status.",
    "UNREADABLE": "ContextResult.UNREADABLE is obsolete. Use "
                  "RedeemStatus.UNREADABLE, read from RedeemResult.status.",
    "UNCONFIRMED": "ContextResult.UNCONFIRMED is obsolete. Use "
                   "RedeemStatus.UNCONFIRMED, read from "
                   "RedeemResult.status.",
}


class _ContextResultType(_EnumMeta):
    """The type of :class:`ContextResult`, which gives a
    :class:`DeprecationWarning` when one of its obsolete members is read by
    name, as in ``ContextResult.EXPIRED``. Reading a member by its value,
    as ``ContextResult("expired")`` does and as this package does, gives
    none, and neither does listing the members."""

    def __getattribute__(cls, name: str) -> Any:
        message = _OBSOLETE_CONTEXT_MEMBERS.get(name)
        if message is not None:
            warnings.warn(message, DeprecationWarning, stacklevel=2)
        return super().__getattribute__(name)


class ContextResult(str, Enum, metaclass=_ContextResultType):
    """The creator context outcome of a redemption, as the cloud reports it
    in the ``context`` field. The values are the cloud's own strings, so a
    result can be compared to a member or printed as received.

    :attr:`EXPIRED`, :attr:`REPLAYED`, :attr:`UNREADABLE` and
    :attr:`UNCONFIRMED` are obsolete, and reading one by name gives a
    :class:`DeprecationWarning`. Read :attr:`RedeemResult.status` instead.
    They keep their values and still work, because the cloud still writes
    those words to ``context`` when a sealed result is not redeemed."""

    #: Every factor matched the browser and connection that created it.
    VERIFIED = "verified"
    #: At least one factor differed. ``factors`` says which.
    MISMATCH = "mismatch"
    #: The identifier carries no creator context.
    NO_CONTEXT = "nocontext"
    #: No longer sent by the service, and kept only because it has been
    #: public since this enumeration was added. What used to give this
    #: answer now gives :attr:`MISCONFIGURED` where the service is at fault,
    #: or :attr:`INVALID_DATE` where the identifier could not have been
    #: created.
    NOT_CHECKABLE = "notcheckable"
    #: The service that checked the identifier could not complete the check,
    #: and the reason is that service rather than the identifier. It either
    #: compared nothing, or compared some factors and reports at least one
    #: as :attr:`FactorResult.MISCONFIGURED`. Nothing a caller sends can
    #: produce it, so it is a signal about the deployment.
    MISCONFIGURED = "misconfigured"
    #: The creation date is one the scheme could not have produced, being in
    #: the future or before the creator context scheme began, so the
    #: identifier is fabricated rather than the service being wrong.
    INVALID_DATE = "invaliddate"
    #: Obsolete. Use :attr:`RedeemStatus.EXPIRED`. The sealed result was
    #: redeemed outside the freshness window.
    EXPIRED = "expired"
    #: Obsolete. Use :attr:`RedeemStatus.REPLAYED`. The sealed result had
    #: already been redeemed on that instance.
    REPLAYED = "replayed"
    #: Obsolete. Use :attr:`RedeemStatus.UNREADABLE`. The sealed result
    #: could not be read. Every cryptographic failure, a missing licence key
    #: included, comes back as this one word by design, and a context string
    #: this package does not know is mapped here too.
    UNREADABLE = "unreadable"
    #: Obsolete. Use :attr:`RedeemStatus.UNCONFIRMED`. First use could not
    #: be confirmed (HTTP 503). The caller may retry.
    UNCONFIRMED = "unconfirmed"


class RedeemStatus(str, Enum):
    """What happened to the sealed result at redemption, as the cloud
    reports it in the ``status`` field. The values are the cloud's own
    words. Only :attr:`SUCCESS` carries an unsealed result, being the
    ``signature``, ``context`` and ``factors`` of the verdict."""

    #: The sealed result was redeemed, and the verdict is in
    #: :attr:`RedeemResult.context`.
    SUCCESS = "success"
    #: The sealed result was redeemed outside the freshness window.
    EXPIRED = "expired"
    #: The sealed result had already been redeemed on that instance.
    REPLAYED = "replayed"
    #: First use could not be confirmed (HTTP 503). The caller may retry.
    UNCONFIRMED = "unconfirmed"
    #: The sealed result could not be read. Every cryptographic failure, a
    #: missing licence key included, comes back as this one word by design,
    #: and a status this package does not know is read as this too.
    UNREADABLE = "unreadable"


class HumanConfidenceValue(str, Enum):
    """The Human Confidence Value a 51Did carries, as the cloud reports it
    in the ``humanConfidence`` field. The values are the cloud's own
    words. The cloud gives it only to a call that presents a License Key
    valid for Human Confidence."""

    #: High confidence that a human was using the device the 51Did was
    #: created for.
    HIGH = "High"
    #: Medium confidence that a human was using the device the 51Did was
    #: created for.
    MEDIUM = "Medium"
    #: Low confidence that a human was using the device the 51Did was
    #: created for.
    LOW = "Low"
    #: The 51Did carries no Value. Every 51Did issued before the Value was
    #: added reads as this.
    ABSENT = "Absent"


class SignatureResult(str, Enum):
    """The signature outcome of a redemption, as the cloud reports it in the
    ``signature`` field of a redeemed result. Absent on every other
    outcome."""

    VERIFIED = "verified"
    INVALID = "invalid"
    #: The cloud did not report the signature, as on an expired result.
    UNKNOWN = "unknown"


class FactorResult(str, Enum):
    """The outcome of one factor in a mismatch or a partly misconfigured
    result. Each value is read only from its own word, and anything else,
    a ``null`` or a word this package does not list, is read as
    :attr:`MISMATCH`, so it never reads as a factor that matched or one
    that could not be compared."""

    VERIFIED = "verified"
    MISMATCH = "mismatch"
    #: The service that checked the identifier is not configured to
    #: determine this factor, so it could not have checked it for any
    #: request. This is NOT a mismatch and must not be read as one, since
    #: the identifier says nothing about it either way.
    MISCONFIGURED = "misconfigured"
    #: The service that created the identifier recorded no value for this
    #: factor, so the identifier says nothing about it and there was
    #: nothing to compare. This is neither a mismatch nor
    #: :attr:`MISCONFIGURED`, which says the checking service could not
    #: determine the factor.
    NOT_RECORDED = "notrecorded"


class SignatureReason(str, Enum):
    """The reason a :meth:`DidClient.verify_signature_detailed` answer was
    given."""

    #: A candidate key verified the signature.
    VERIFIED = "verified"
    #: The envelope version is not the one the cloud signs.
    VERSION = "version"
    #: The payload is shorter than the base length for its type.
    LENGTH = "length"
    #: No published key covers the identifier's date.
    NO_KEY = "nokey"
    #: Every candidate key was tried and none verified the signature.
    SIGNATURE = "signature"


class DidClientError(Exception):
    """An answer from the cloud that was not the one asked for. Carries the
    HTTP status and the response body so a caller can relay or log what the
    cloud said."""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 body: Optional[str] = None) -> None:
        super().__init__(message)
        #: The HTTP status, where there was one.
        self.status_code = status_code
        #: The response body, where there was one.
        self.body = body


class DidArgumentError(DidClientError, ValueError):
    """The 51Did given to a cloud call was not a valid identifier. Raised by
    the client itself, before any transport, when the text does not parse
    as a 51Did, with the message naming the
    :class:`~fiftyone_pipeline_did.FodIdParseStatus` and no status code,
    and raised for a cloud answer of HTTP 400 with an ``errors`` list, with
    the cloud's own text and the status code. Also a :class:`ValueError`,
    the language's argument error."""


class DidNotSupportedError(DidClientError):
    """The host answering does not offer the creator context (HTTP 404 from
    the redeem endpoint). A caller can name this case rather than treat it
    as a failed check."""


@dataclass(frozen=True)
class PublicKeyEntry:
    """A published signing key and the period it is in force, from its
    start until its end, or until the next key starts where the cloud sent
    no end."""

    #: When the key came, or comes, into force, as an aware UTC datetime.
    starts_at: datetime
    #: The key in SPKI PEM form.
    public_key: str
    #: When the key stops being in force, as an aware UTC datetime, or
    #: ``None`` where the cloud sent no end. A key replaced before its
    #: scheduled end carries the moment it was replaced.
    ends_at: Optional[datetime] = None


@dataclass(frozen=True)
class SignatureCheck:
    """The detailed answer to an offline signature check."""

    #: Whether a candidate key verified the signature.
    valid: bool
    #: Why the answer was given.
    reason: SignatureReason


@dataclass(frozen=True)
class CloudVerification:
    """The detailed answer to a signature check through the cloud's verify
    endpoint, from :meth:`DidClient.verify_detailed`."""

    #: Whether the cloud verified the signature.
    valid: bool
    #: The Human Confidence Value the 51Did carries, present only where the
    #: signature verified and the call presented a License Key valid for
    #: Human Confidence. ``None`` otherwise. A Value this package does not
    #: know reads as :attr:`HumanConfidenceValue.ABSENT`.
    human_confidence: Optional[HumanConfidenceValue] = None
    #: Why the cloud gave no Human Confidence Value, as the cloud worded
    #: it, where it said, or :data:`NO_HUMAN_CONFIDENCE_REASON` where the
    #: signature verified and the answer held neither a Value nor a
    #: reason. ``None`` otherwise.
    human_confidence_null_reason: Optional[str] = None
    #: The ``humanConfidence`` string exactly as the cloud sent it, or
    #: ``None`` where it sent none, kept so a word this package does not
    #: know is still visible.
    human_confidence_raw: Optional[str] = None


#: The type of a factor value in :attr:`RedeemResult.factors`, which is
#: never ``None``.
FactorValue = FactorResult

#: The shape of an injected transport: an async callable taking the
#: prepared :class:`urllib.request.Request` and answering the HTTP status
#: and the response body, whatever the status. An object with an ``open``
#: method (an :class:`urllib.request.OpenerDirector`) is accepted as well,
#: and its blocking ``open`` runs on a worker thread as the default
#: transport does.
Transport = Callable[[urllib.request.Request], Awaitable[Tuple[int, bytes]]]

_ISO_8601 = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?"
    r"(Z|[+-]\d{2}:?\d{2})?$")


def parse_iso8601(text: str) -> datetime:
    """Parses an ISO 8601 date and time as the cloud writes one, with any
    number of fractional second digits and ``Z`` or an offset, into an
    aware UTC datetime. Raises :class:`ValueError` for anything else.

    Written here rather than through :meth:`datetime.fromisoformat`,
    because on Python 3.9 and 3.10 that method takes neither ``Z`` nor the
    seven fractional digits the cloud emits.
    """
    match = _ISO_8601.match(text.strip())
    if match is None:
        raise ValueError("not an ISO 8601 date and time: {0!r}".format(text))
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    microsecond = int((fraction or "0")[:6].ljust(6, "0"))
    value = datetime(int(year), int(month), int(day), int(hour),
                     int(minute), int(second), microsecond,
                     tzinfo=timezone.utc)
    if zone and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        digits = zone[1:].replace(":", "")
        offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        value = value - sign * offset
    return value


def _try_parse_json(text: str) -> Any:
    """Parses JSON without raising, answering ``None`` for text that is not
    JSON."""
    try:
        return json.loads(text)
    except ValueError:
        return None


class RedeemResult:
    """The typed answer to a redemption. Built from the cloud's JSON body,
    with the raw status and body kept for logging."""

    def __init__(self, status_code: int, raw: str,
                 parsed: Dict[str, Any]) -> None:
        """Reads ``parsed`` as given. :meth:`from_response` is the way to
        read a response, as it applies what the HTTP status means."""
        #: The HTTP status the cloud answered with, 200 or 503.
        self.status_code = status_code
        #: The response body exactly as received.
        self.raw = raw
        context = parsed.get("context")
        context = context if isinstance(context, str) else ""
        #: The ``context`` string exactly as the cloud sent it, kept so an
        #: outcome this package does not know is still visible.
        self.context_raw = context
        #: One of :class:`ContextResult`. A string this package does not
        #: know maps to :attr:`ContextResult.UNREADABLE`, so an
        #: unrecognised outcome is never mistaken for a good one. HTTP 503
        #: reads as ``unconfirmed``, whatever the body says.
        self.context = _context_of(context)
        status = parsed.get("status")
        status = status if isinstance(status, str) else ""
        #: The ``status`` string exactly as the cloud sent it, or ``""``
        #: where it sent none, kept so a status this package does not know
        #: is still visible.
        self.status_raw = status
        #: One of :class:`RedeemStatus`, saying what happened to the sealed
        #: result. Only :attr:`RedeemStatus.SUCCESS` carries a verdict. A
        #: status this package does not know reads as
        #: :attr:`RedeemStatus.UNREADABLE`, so it is never mistaken for a
        #: good one. A cloud that sends no ``status`` writes the same word
        #: to ``context`` on every other outcome, so the status is then read
        #: from ``context``. HTTP 503 is always
        #: :attr:`RedeemStatus.UNCONFIRMED`, whatever the body says.
        self.status = _status_of(status, context)
        value, word, reason = _human_confidence_fields(
            parsed, self.status is RedeemStatus.SUCCESS)
        #: The ``humanConfidence`` string exactly as the cloud sent it, or
        #: ``None`` where it sent none, kept so a word this package does
        #: not know is still visible.
        self.human_confidence_raw: Optional[str] = word
        #: The Human Confidence Value the 51Did carries, one of
        #: :class:`HumanConfidenceValue`. The cloud gives it on
        #: :attr:`RedeemStatus.SUCCESS` to a call that presented a License
        #: Key valid for Human Confidence. ``None`` where the cloud sent no
        #: Value. A Value this package does not know reads as
        #: :attr:`HumanConfidenceValue.ABSENT`, so it is never mistaken
        #: for one of the others.
        self.human_confidence: Optional[HumanConfidenceValue] = value
        #: Why the cloud gave no Human Confidence Value, as the cloud worded
        #: it, where it said, or :data:`NO_HUMAN_CONFIDENCE_REASON` where the
        #: status is :attr:`RedeemStatus.SUCCESS` and the answer held
        #: neither a Value nor a reason. ``None`` otherwise.
        self.human_confidence_null_reason: Optional[str] = reason
        signature = parsed.get("signature")
        #: One of :class:`SignatureResult`.
        self.signature = (
            SignatureResult.VERIFIED if signature == "verified"
            else SignatureResult.INVALID if signature == "invalid"
            else SignatureResult.UNKNOWN)
        factors = parsed.get("factors")
        #: Factor name to :class:`FactorResult`, present only when the cloud
        #: sent ``factors``, which is where there is something to diagnose.
        #: A ``null`` factor reads as :attr:`FactorResult.MISMATCH`, as
        #: every value other than the four words does. The names are
        #: ``transport``, ``device``, ``browserip``, ``connectionip``,
        #: ``asn``, ``platformname``, ``platformversion``, ``browsername``
        #: and ``browserversion``. A version mismatch beside a verified
        #: name means an upgrade, whilst a mismatched name means a
        #: different operating system or browser. The names are taken as
        #: the cloud sent them, so a name this package does not list is
        #: kept under its own key rather than read as one of these.
        self.factors: Optional[Dict[str, FactorValue]] = (
            {str(name): _factor_of(value) for name, value in factors.items()}
            if isinstance(factors, dict) else None)
        verified_at = parsed.get("verifiedAt")
        #: When the verify endpoint checked the context and sealed the
        #: result, present on the redeemed and expired outcomes.
        self.verified_at: Optional[datetime] = None
        if isinstance(verified_at, str):
            try:
                self.verified_at = parse_iso8601(verified_at)
            except ValueError:
                self.verified_at = None
        seconds = parsed.get("secondsSinceVerified")
        #: Whole seconds between the sealing and this redemption by the
        #: cloud's clock, present on the redeemed and expired outcomes.
        self.seconds_since_verified: Optional[int] = (
            int(seconds)
            if isinstance(seconds, (int, float))
            and not isinstance(seconds, bool) else None)

    @classmethod
    def from_response(cls, status_code: int, raw: str) -> "RedeemResult":
        """Builds a result from a redeem response body. A 503 is
        :attr:`RedeemStatus.UNCONFIRMED`, with ``unconfirmed`` as both the
        raw status and the context, whatever its body, and nothing else is
        read from it. A body that is not a JSON object, or one holding
        neither ``status`` nor ``context``, is
        :attr:`RedeemStatus.UNREADABLE`, with ``unreadable`` as both the raw
        status and the context and the signature
        :attr:`SignatureResult.UNKNOWN`, and nothing else is read from it.
        Neither raises."""
        if status_code == 503:
            # First use could not be confirmed. The body is kept in raw but
            # never read, so a body shaped like a redeemed result gives no
            # verdict, Value, signature, factors or times.
            return cls(status_code, raw,
                       {"status": "unconfirmed", "context": "unconfirmed"})
        parsed = _try_parse_json(raw)
        if not isinstance(parsed, dict) or not (
                isinstance(parsed.get("status"), str)
                or isinstance(parsed.get("context"), str)):
            # Nothing says what happened, so no member of the body is
            # trusted, a signature included, and nothing reads as a pass.
            return cls(status_code, raw,
                       {"status": "unreadable", "context": "unreadable"})
        return cls(status_code, raw, parsed)

    def to_dict(self) -> Dict[str, Any]:
        """The result in the cloud's own response shape (``signature``,
        ``context``, ``factors`` when present, ``verifiedAt``,
        ``secondsSinceVerified``), so a server can answer a page with it
        directly. ``signature`` is left out when the cloud did not report
        it, as the cloud leaves it out. ``status`` is left out, as the
        failure words are in ``context``, and so is the Human Confidence
        Value, which is for the server holding the License Key and never
        for the page."""
        body: Dict[str, Any] = {}
        if self.signature is not SignatureResult.UNKNOWN:
            body["signature"] = self.signature.value
        body["context"] = self.context.value
        if self.factors is not None:
            body["factors"] = {
                name: value.value for name, value in self.factors.items()}
        if self.verified_at is not None:
            # ISO 8601 UTC to the second, as the cloud writes it.
            body["verifiedAt"] = self.verified_at.astimezone(
                timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.seconds_since_verified is not None:
            body["secondsSinceVerified"] = self.seconds_since_verified
        return body

    def __repr__(self) -> str:
        return "RedeemResult(status_code={0}, context={1!r})".format(
            self.status_code, self.context_raw)


def _context_of(text: str) -> ContextResult:
    # Read by value, so the package itself never reads an obsolete member
    # by name and never gives the warning that reading does.
    try:
        return ContextResult(text)
    except ValueError:
        return ContextResult("unreadable")


# The context words that are a verdict the check reached, so an answer
# without status that holds one of them was redeemed. Kept apart from
# ContextResult, which also lists notcheckable, a word that is no verdict.
_VERDICT_WORDS = frozenset((
    "verified", "mismatch", "nocontext", "misconfigured", "invaliddate"))


def _status_of(status: str, context: str) -> RedeemStatus:
    """The status of a redemption. Read from ``status`` where the cloud sent
    one, and otherwise from ``context``: Success for one of the five
    verdicts, the word itself for one of the four reasons (expired,
    replayed, unreadable and unconfirmed), and Unreadable for any other
    word or none, so a word this package does not know is never a pass."""
    if status != "":
        try:
            return RedeemStatus(status)
        except ValueError:
            return RedeemStatus.UNREADABLE
    if context in _VERDICT_WORDS:
        return RedeemStatus.SUCCESS
    # "success" is a status word only, so as a context it is unknown.
    if context != RedeemStatus.SUCCESS.value:
        try:
            return RedeemStatus(context)
        except ValueError:
            pass
    return RedeemStatus.UNREADABLE


def _human_confidence_of(value: Any) -> Optional[HumanConfidenceValue]:
    """The Human Confidence Value from the cloud's word, compared without
    regard to case. ``None`` where the cloud sent no Value (the field left
    out, or ``null``), and :attr:`HumanConfidenceValue.ABSENT` for any
    other value this package does not know, so it is never taken for High,
    Medium or Low."""
    if value is None:
        return None
    if isinstance(value, str):
        for member in HumanConfidenceValue:
            if member.value.lower() == value.lower():
                return member
    return HumanConfidenceValue.ABSENT


def _human_confidence_fields(parsed: Dict[str, Any], answered: bool) \
        -> Tuple[Optional[HumanConfidenceValue], Optional[str],
                 Optional[str]]:
    """The Human Confidence fields of a verify or redeem answer: the Value,
    the ``humanConfidence`` word exactly as sent, and the null reason. The
    word is ``None`` where the cloud sent no string. Where ``answered`` is
    set, because the answer verified or redeemed the 51Did, and the cloud
    sent neither a Value nor a reason, as a cloud from before the Value
    does, the reason is :data:`NO_HUMAN_CONFIDENCE_REASON`."""
    word = parsed.get("humanConfidence")
    reason = parsed.get("humanConfidenceNullReason")
    word = word if isinstance(word, str) else None
    reason = reason if isinstance(reason, str) else None
    if answered and reason is None and \
            parsed.get("humanConfidence") is None:
        reason = NO_HUMAN_CONFIDENCE_REASON
    return (_human_confidence_of(parsed.get("humanConfidence")), word,
            reason)


def _factor_of(value: Any) -> FactorValue:
    # The cloud writes lower case words, and the comparison ignores case.
    if isinstance(value, str):
        value = value.lower()
    if value == "verified":
        return FactorResult.VERIFIED
    if value == "mismatch":
        return FactorResult.MISMATCH
    # Each read on its own rather than left to fall through, because
    # neither is a mismatch and neither must ever be taken for one.
    if value == "misconfigured":
        return FactorResult.MISCONFIGURED
    if value == "notrecorded":
        return FactorResult.NOT_RECORDED
    # Anything else is a mismatch, a null and a word a newer service sends
    # included, so it never reads as a factor that matched or one that could
    # not be compared.
    return FactorResult.MISMATCH


class DidClient:
    """Everything a server does with a 51Did against the 51Degrees cloud.

    Every method that reaches the cloud is a coroutine and must be awaited.
    The public key list is cached per instance with the time it was
    fetched, behind an asyncio lock, so one instance serves a whole server
    on its event loop and concurrent awaits for the list share one fetch
    rather than each making its own.

    :param resource_key: the page's resource key. Required. Public by
        nature, it travels in the route of the key and verify requests and
        in the form body of the redeem request.
    :param licence_key: a licence key of the same account. Server side
        only. Needed to redeem where the account holds licence keys, and
        sent only in the body of the redeem request, never in a URL.
    :param endpoint: the API base including the ``/api/v4/`` segment.
        Defaults to the ``_51DEGREES_CLOUD_ENDPOINT`` environment variable,
        then to the public cloud. A value without a trailing slash gains
        one.
    :param transport: the HTTP transport, either an async callable taking
        the prepared :class:`urllib.request.Request` and answering
        ``(status, body_bytes)``, or an
        :class:`urllib.request.OpenerDirector`. The default runs
        :func:`urllib.request.urlopen` on a worker thread through
        :func:`asyncio.to_thread`, which is blocking I/O kept off the
        event loop rather than non-blocking I/O, so supply an ``aiohttp``
        or ``httpx`` based transport for a fully non-blocking one. Tests
        inject one.
    :param now: the clock, returning an aware UTC datetime. Defaults to
        :meth:`datetime.now` in UTC. Tests inject one.
    :param timeout: seconds the default transport waits for the cloud.
    """

    def __init__(self, resource_key: str, licence_key: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 transport: Optional[Any] = None,
                 now: Optional[Callable[[], datetime]] = None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        if not isinstance(resource_key, str) or resource_key == "":
            raise ValueError("resource_key is required")
        self._resource_key = resource_key
        self._licence_key = licence_key if licence_key else None
        base = endpoint or _endpoint_from_environment() or \
            DEFAULT_ENDPOINT
        # Normalised to end in exactly one slash so every URL is the base
        # plus a relative path, as the cloud request engine treats the same
        # value.
        self._endpoint = base.rstrip("/") + "/"
        self._transport = transport
        self._timeout = timeout
        self._now = now or (lambda: datetime.now(timezone.utc))
        # Created on first use inside a running event loop, and made again
        # when a different loop uses the client, because an asyncio lock
        # belongs to the event loop it is first used on. See _loop_lock.
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._keys: Optional[List[PublicKeyEntry]] = None
        # When the whole list was last fetched, which the daily refresh
        # is measured from.
        self._fetched_at: Optional[datetime] = None
        # When a fetch that the once a minute limit counts was last
        # started, which the limit is measured from.
        self._refetched_at: Optional[datetime] = None
        self._fetch_count = 0

    @property
    def endpoint(self) -> str:
        """The API base every request is built on."""
        return self._endpoint

    @property
    def resource_key(self) -> str:
        """The resource key the requests carry."""
        return self._resource_key

    @property
    def has_licence_key(self) -> bool:
        """Whether the client was given a licence key. A licence key is
        needed only by :meth:`redeem`, so a client without one still
        reads keys and verifies signatures."""
        return self._licence_key is not None

    # ----- Public keys and key selection -----

    async def public_keys(self) -> List[PublicKeyEntry]:
        """The published signing keys, oldest first, fetched on first use
        and then served from the cache, which is fetched again, whole, once
        it is a day old. Every answer is merged into the keys held, so no
        key is dropped and 51Dids made long ago still verify. Concurrent
        awaits while a fetch is in flight wait for that fetch and share its
        answer."""
        async with self._loop_lock():
            return list(await self._current_keys_locked())

    async def public_key_for(self, fod_id: Union[FodId, str]) \
            -> Optional[PublicKeyEntry]:
        """The key in force when the identifier was created, being the
        entry whose start is latest on or before the identifier's date,
        unless that entry had ended by then. The keys held answer every
        date before the newest key's end, or before its start where the
        cloud sent no end. For a date near or past that point the list is
        fetched again first, asking only for the keys from the newest start
        held, at most once a minute. The whole list is also fetched again
        once it is a day old. Answers ``None`` when no key held was in
        force at the date."""
        identifier = _as_fod_id(fod_id)
        date = _date_of(identifier)
        keys, _ = await self._keys_for(date)
        return _in_force_at(keys, date)

    # ----- Offline signature verification -----

    async def verify_signature(self, fod_id: Union[FodId, str]) -> bool:
        """Verifies the identifier's signature offline against the
        published keys, as the cloud's own verify endpoint does. The
        envelope version must be the one the cloud signs, the payload must
        be at least the base length for its type (a longer payload carries
        a creator context and is accepted), and the signature must verify
        against the key in force at the identifier's date or, near a
        period boundary, the neighbouring key. No earlier key is ever
        tried. Reaches the cloud only when the key list needs fetching,
        which includes once after a signature fails with every candidate
        key, asking for the keys from the one in force at the identifier's
        date, at most once a minute, because a key may be replaced before
        its end."""
        return (await self.verify_signature_detailed(fod_id)).valid

    async def verify_signature_detailed(self, fod_id: Union[FodId, str]) \
            -> SignatureCheck:
        """As :meth:`verify_signature`, with the reason alongside the
        answer, so a caller can tell an identifier no key covers from one
        whose signature failed."""
        identifier = _as_fod_id(fod_id)
        if identifier.version != SUPPORTED_VERSION:
            return SignatureCheck(False, SignatureReason.VERSION)
        if not _payload_length_valid(identifier):
            return SignatureCheck(False, SignatureReason.LENGTH)
        date = _date_of(identifier)
        keys, fetched = await self._keys_for(date)
        candidates = _candidates_for_date(keys, date)
        if not candidates:
            return SignatureCheck(False, SignatureReason.NO_KEY)
        if _verified_by_any(identifier, candidates):
            return SignatureCheck(True, SignatureReason.VERIFIED)
        # The key held may have been replaced before its end, so within the
        # once a minute limit the check is repeated with the list fetched
        # again before a failure is reported. A list fetched for this very
        # call cannot get better.
        keys = None if fetched else await self._keys_after_failure(date)
        if keys is not None:
            candidates = _candidates_for_date(keys, date)
            if not candidates:
                return SignatureCheck(False, SignatureReason.NO_KEY)
            if _verified_by_any(identifier, candidates):
                return SignatureCheck(True, SignatureReason.VERIFIED)
        return SignatureCheck(False, SignatureReason.SIGNATURE)

    # ----- Cloud signature verification -----

    async def verify(self, fod_id: Union[FodId, str]) -> bool:
        """Verifies the identifier's signature through the cloud's verify
        endpoint, the open endpoint that needs no licence key. One use
        against the resource key.

        Raises :class:`DidArgumentError` (also a :class:`ValueError`)
        before transport when a string does not parse as a 51Did, with the
        message naming the parse status, or when the cloud refused the
        value, with the cloud's message, and :class:`DidClientError` on any
        answer other than valid or invalid. Only an HTTP 200 answer can be
        valid. An HTTP 400 answer is invalid whatever its body says, and
        any other status raises :class:`DidClientError` whatever its body
        says. Text far longer than any
        identifier raises :class:`ValueError` before transport. A
        transport failure raises the :class:`OSError` the transport raised
        (:class:`urllib.error.URLError` by default). Being a coroutine,
        every one of these is raised when the call is awaited."""
        return (await self._verify(fod_id, False)).valid

    async def verify_detailed(self, fod_id: Union[FodId, str]) \
            -> CloudVerification:
        """As :meth:`verify`, with the Human Confidence Value the 51Did
        carries alongside the answer.

        Where the client holds a licence key, it is sent in the
        ``X-51D-License-Key`` header, never in the URL, and the cloud adds
        the Value for a 51Did whose signature verifies when that key is
        valid for Human Confidence. Otherwise the answer carries the reason
        the cloud gave for leaving the Value out, where it gave one.
        :meth:`verify` sends no licence key. One use against the resource
        key, as :meth:`verify` is. Raises what :meth:`verify` raises."""
        return await self._verify(fod_id, True)

    async def _verify(self, fod_id: Union[FodId, str],
                      with_licence: bool) -> CloudVerification:
        """The verify request, with the licence key in its header where
        ``with_licence`` is set and the client holds one."""
        text = _identifier_text(fod_id)
        # The identifier travels under both names so the request works with
        # hosts that read either parameter. Hosts that recognise both prefer
        # 51did and keep owid as a compatibility alias.
        encoded = urllib.parse.quote(text, safe="")
        url = "{0}id/verify/{1}?51did={2}&owid={2}".format(
            self._endpoint, urllib.parse.quote(self._resource_key, safe=""),
            encoded)
        headers = {"User-Agent": USER_AGENT}
        if with_licence and self._licence_key is not None:
            headers[_LICENCE_HEADER] = self._licence_key
        status, body = await self._send(urllib.request.Request(
            url, headers=headers, method="GET"))
        parsed = _try_parse_json(body)
        # Only a 200 can verify, and only a 200 carries the Human
        # Confidence fields. A 400 is invalid whatever its body says.
        # Every other status is an error, whatever its body says.
        if isinstance(parsed, dict) and status in (200, 400):
            valid = parsed.get("valid")
            if status == 200 and isinstance(valid, bool):
                value, word, reason = _human_confidence_fields(parsed, valid)
                return CloudVerification(valid, value, reason, word)
            if status == 400 and isinstance(valid, bool):
                return CloudVerification(False)
            errors = parsed.get("errors")
            if status == 400 and isinstance(errors, list):
                raise DidArgumentError(
                    " ".join(str(e) for e in errors), status, body)
        raise DidClientError(
            "Verify answered HTTP {0}: {1}".format(status, body), status,
            body)

    # ----- Redeem -----

    async def redeem(self, fod_id: Union[FodId, str],
                     sealed_result: Optional[str] = _NOT_GIVEN,
                     transaction: Optional[str] = None, *,
                     result: Optional[str] = _NOT_GIVEN,
                     challenge: Optional[str] = _NOT_GIVEN) -> RedeemResult:
        """Redeems a sealed creator context result against the identifier,
        on the server, with the licence key.

        The resource key, the 51Did, the sealed result, the transaction and
        the licence key all travel in the body of a POST to ``id/redeem``,
        as ``resource``, ``51did``, ``sealedResult``, ``transaction`` and
        ``license``, so none of them reaches an access log. The sealed
        result and the transaction are also sent under their obsolete names,
        ``result`` and ``challenge``, so the call works with a cloud that
        reads only those. (The redeem
        endpoint takes the resource key in the form on a POST, where the
        key and verify endpoints take it in the route on a GET.) One use
        against the resource key, the second of the two a browser context
        check costs.

        A 200 and a 503 both produce a result, the 503 being the
        ``unconfirmed`` status the caller may retry. Every cryptographic
        failure comes back as the one word ``unreadable`` by design, so the
        client does not try to tell them apart either. Read
        :attr:`RedeemResult.status` for what happened to the sealed result,
        and :attr:`RedeemResult.human_confidence` for the Human Confidence
        Value the 51Did carries.

        :param fod_id: the identifier the caller knows independently, or
            its base64 in either alphabet.
        :param sealed_result: the sealed result exactly as the verify
            endpoint returned it to the page.
        :param transaction: the single-use transaction value given to the
            verify endpoint, where one was.
        :param result: obsolete. Use ``sealed_result``. Still works, with a
            :class:`DeprecationWarning`, and ``sealed_result`` wins when
            both are given.
        :param challenge: obsolete. Use ``transaction``. Still works, with a
            :class:`DeprecationWarning`, and ``transaction`` wins when both
            are given.
        :raises TypeError: when neither ``sealed_result`` nor ``result`` is
            given.
        :raises DidArgumentError: before transport when a string does not
            parse as a 51Did, with the message naming the parse status, or
            when the cloud refused the value (HTTP 400), with the cloud's
            message.
        :raises ValueError: before transport when the text is far longer
            than any identifier.
        :raises DidNotSupportedError: when the host does not offer the
            creator context (HTTP 404).
        :raises DidClientError: on any other status.
        :raises OSError: when the transport failed to reach the cloud
            (:class:`urllib.error.URLError` by default).

        Being a coroutine, every one of these is raised when the call is
        awaited.
        """
        if result is not _NOT_GIVEN:
            warnings.warn(
                "The result argument of redeem is obsolete. Use "
                "sealed_result.", DeprecationWarning, stacklevel=2)
            if sealed_result is _NOT_GIVEN:
                sealed_result = result
        if challenge is not _NOT_GIVEN:
            warnings.warn(
                "The challenge argument of redeem is obsolete. Use "
                "transaction.", DeprecationWarning, stacklevel=2)
            if transaction is None:
                transaction = challenge
        if sealed_result is _NOT_GIVEN:
            raise TypeError("redeem() missing the sealed_result argument")
        text = _identifier_text(fod_id)
        sealed_text = sealed_result if isinstance(sealed_result, str) else ""
        transaction_text = (
            transaction if isinstance(transaction, str) else "")
        # Each value is sent under its new name and its obsolete one, so the
        # call works with a cloud that reads only the obsolete names. A cloud
        # that reads both takes the new name and adds an "obsolete" array to
        # its answer, which is ignored here.
        form = [
            ("resource", self._resource_key),
            ("51did", text),
            ("sealedResult", sealed_text),
            ("transaction", transaction_text),
            ("result", sealed_text),
            ("challenge", transaction_text),
        ]
        if self._licence_key is not None:
            form.append(("license", self._licence_key))
        url = self._endpoint + "id/redeem"
        status, body = await self._send(urllib.request.Request(
            url,
            data=urllib.parse.urlencode(form).encode("ascii"),
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST"))
        if status in (200, 503):
            return RedeemResult.from_response(status, body)
        if status == 400:
            parsed = _try_parse_json(body)
            errors = parsed.get("errors") if isinstance(parsed, dict) \
                else None
            message = " ".join(str(e) for e in errors) \
                if isinstance(errors, list) else body
            raise DidArgumentError(message, status, body)
        if status == 404:
            raise DidNotSupportedError(
                "The host does not offer the creator context: " + body,
                status, body)
        raise DidClientError(
            "Redeem answered HTTP {0}: {1}".format(status, body), status,
            body)

    # ----- Internals -----

    async def _send(self, request: urllib.request.Request) \
            -> Tuple[int, str]:
        """Sends the request through the transport and answers the status
        and the body as text, whatever the status. A non-2xx answer is an
        answer, not an exception, so each caller can read what the cloud
        said. Only a failure to reach the cloud raises, as the
        :class:`OSError` the transport raised.

        The default transport and an opener both block, so they run on a
        worker thread through :func:`asyncio.to_thread` and the event loop
        stays free while the cloud answers. An injected callable must be
        an async one, and a plain callable is refused by name rather than
        left to fail on the await, so the mistake reads as what it is."""
        transport = self._transport
        if transport is None:
            status, body = await asyncio.to_thread(
                _urlopen,
                lambda: urllib.request.urlopen(request,
                                               timeout=self._timeout))
        elif hasattr(transport, "open"):
            status, body = await asyncio.to_thread(
                _urlopen,
                lambda: transport.open(request, timeout=self._timeout))
        else:
            answer = transport(request)
            if not inspect.isawaitable(answer):
                raise TypeError(
                    "transport must be an async callable answering "
                    "(status, body), or an object with an open method")
            status, body = await answer
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        return int(status), body

    def _loop_lock(self) -> asyncio.Lock:
        """The lock guarding the key cache, for the running event loop.

        An asyncio lock belongs to the event loop it is first used on, so
        a client used from a second loop (a script calling
        :func:`asyncio.run` more than once, or a test doing the same)
        would otherwise fail with a lock bound to a loop that has gone.
        A fresh lock is made for the new loop instead. A client is used
        from one thread's loop at a time, as any asyncio object is, so the
        check and the swap cannot interleave."""
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    async def _current_keys_locked(self) -> List[PublicKeyEntry]:
        if self._keys is None or self._stale():
            return await self._refresh_locked()
        return self._keys

    async def _keys_for(self, date: datetime) \
            -> Tuple[List[PublicKeyEntry], bool]:
        """The key list to select from for the given date, and whether it
        was fetched for this call. It is fetched again first where the date
        is near or past the end of what the keys held cover, asking for the
        keys from the newest start held, within the once a minute limit.

        The fetch count is read before waiting for the lock, so a fetch
        that completes while this call waits counts as this call's own,
        and concurrent awaits for a date the keys held do not cover share
        that one fetch instead of each fetching again after the other."""
        fetched_before = self._fetch_count
        async with self._loop_lock():
            keys = await self._current_keys_locked()
            if self._fetch_count == fetched_before \
                    and not _covers(keys, date) \
                    and self._may_refetch():
                keys = await self._refetch_locked(
                    keys[-1].starts_at if keys else None)
            return keys, self._fetch_count != fetched_before

    async def _keys_after_failure(self, date: datetime) \
            -> Optional[List[PublicKeyEntry]]:
        """The key list fetched again after a signature failed with every
        key that could have signed it, or ``None`` where the once a minute
        limit stops the fetch. The keys are asked for from the start of the
        key held in force at the date, so the answer carries that key's
        entry, with any earlier end, and a replacement starting inside its
        period."""
        async with self._loop_lock():
            if not self._may_refetch():
                return None
            return await self._refetch_locked(_started_by(self._keys, date))

    def _stale(self) -> bool:
        return self._fetched_at is None \
            or self._now() - self._fetched_at > KEY_LIST_MAX_AGE

    def _may_refetch(self) -> bool:
        """Whether the once a minute limit allows a fetch for a date the
        keys held do not cover or after a failed signature. A clock set back
        is no reason to wait, so only a fetch started less than the interval
        in the past holds the next one back."""
        if self._refetched_at is None:
            return True
        elapsed = self._now() - self._refetched_at
        return elapsed < timedelta(0) or elapsed >= _REFETCH_INTERVAL

    async def _refetch_locked(self, since: Optional[datetime]) \
            -> List[PublicKeyEntry]:
        """Fetches the keys starting at or after ``since``, as a fetch the
        once a minute limit counts. The limit is measured from before the
        request, so a failed attempt counts as well."""
        self._refetched_at = self._now()
        return await self._refresh_locked(since)

    async def _refresh_locked(self, since: Optional[datetime] = None) \
            -> List[PublicKeyEntry]:
        """Fetches the key list and merges the answer into the keys held.
        Without ``since`` the whole list is asked for, as on first use and
        once a day, and only that restarts the list's age, because a key
        replaced while it is not the newest held may otherwise go unseen,
        and this refresh bounds how long a replaced key is trusted offline.
        With ``since`` only the keys starting at or after it are asked
        for."""
        answer = await self._fetch_keys(since)
        self._keys = _merge(self._keys or [], answer)
        if since is None:
            self._fetched_at = self._now()
        self._fetch_count += 1
        return self._keys

    async def _fetch_keys(self, since: Optional[datetime] = None) \
            -> List[PublicKeyEntry]:
        """GET ``id/key/{resource}`` and read each entry's start, end and
        public key. ``startsAt`` is read where present and ``created``
        otherwise. Both are supported start fields in key-list responses.
        ``endsAt`` is read where present and not null. ``weekStart`` is
        ignored. With ``since``, the ``datetime`` query parameter asks only
        for the keys that start at or after it."""
        url = "{0}id/key/{1}".format(
            self._endpoint, urllib.parse.quote(self._resource_key, safe=""))
        if since is not None:
            url += "?datetime=" + urllib.parse.quote(
                _format_iso8601(since), safe="")
        status, body = await self._send(urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT}, method="GET"))
        if status != 200:
            raise DidClientError(
                "Public keys answered HTTP {0}: {1}".format(status, body),
                status, body)
        parsed = _try_parse_json(body)
        if not isinstance(parsed, list):
            raise DidClientError(
                "Public keys answered with a body that is not a JSON "
                "array: " + body, status, body)
        keys = []
        for entry in parsed:
            start = end = public_key = None
            if isinstance(entry, dict):
                start = entry.get("startsAt") or entry.get("created")
                end = entry.get("endsAt")
                public_key = entry.get("publicKey")
            starts_at = _moment_of(start)
            if starts_at is None or not isinstance(public_key, str):
                raise DidClientError(
                    "Public keys entry lacks a start or a publicKey: "
                    + json.dumps(entry), status, body)
            ends_at = None if end is None else _moment_of(end)
            if end is not None and ends_at is None:
                raise DidClientError(
                    "Public keys entry has an end that is not a date and "
                    "time: " + json.dumps(entry), status, body)
            if ends_at is not None and ends_at <= starts_at:
                raise DidClientError(
                    "Public keys entry does not end after it starts: "
                    + json.dumps(entry), status, body)
            keys.append(PublicKeyEntry(starts_at, public_key, ends_at))
        keys.sort(key=lambda key: key.starts_at)
        return keys


def _urlopen(open_call: Callable[[], Any]) -> Tuple[int, bytes]:
    """Runs a urllib open and answers the status and body whatever the
    status, since urllib raises for anything outside 2xx and the error is
    itself the response. A failure to reach the host propagates as the
    :class:`urllib.error.URLError` (an :class:`OSError`) it raised. This
    blocks, so :meth:`DidClient._send` runs it on a worker thread."""
    try:
        with open_call() as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        body = error.read()
        error.close()
        return error.code, body


def _as_fod_id(value: Union[FodId, str]) -> FodId:
    """The identifier as a FodId, parsing a base64 string where one was
    given. The parse happens here, before any key is fetched, so text that
    is not a 51Did raises what :meth:`FodId.from_base64` raises and never
    reaches the cloud. A caller who would rather have the reason than an
    exception parses with :meth:`FodId.try_from_base64` first."""
    if isinstance(value, FodId):
        return value
    if isinstance(value, str):
        _ensure_encoded_size(value)
        return FodId.from_base64(value)
    raise TypeError("fod_id must be a FodId or a base64 string")


def _identifier_text(value: Union[FodId, str]) -> str:
    """The text sent to the cloud for an identifier. A parsed identifier
    goes in the URL-safe alphabet, which needs no further encoding, and a
    string goes as given, in whichever alphabet and padding it arrived,
    once the client has checked that the string parses as a 51Did, so a
    value that is not one never reaches the cloud."""
    if isinstance(value, FodId):
        return value.as_base64_url()
    if isinstance(value, str) and value != "":
        _ensure_encoded_size(value)
        _ensure_parses(value)
        return value
    raise TypeError("fod_id must be a FodId or a non-empty base64 string")


def _ensure_parses(value: str) -> None:
    """Refuses text that is not a 51Did before any transport, naming the
    parse status in the client's argument error. The signature is not
    checked here, as the cloud call is what checks it."""
    result = FodId.try_from_base64(value)
    if not result.ok:
        raise DidArgumentError(
            "The identifier is not a 51Did: {0}.".format(
                result.status.value))


def _ensure_encoded_size(value: str) -> None:
    """Refuses obviously malformed text before it is parsed, a key is
    fetched or the cloud is called. White space around the value is
    removed before measuring, as the reader removes it before decoding,
    so the two measure the same characters."""
    if len(_trim_white_space(value)) > _MAXIMUM_ENCODED_LENGTH:
        raise ValueError(
            "The identifier is far longer than any 51Did the cloud "
            "issues.")


def _date_of(fod_id: FodId) -> datetime:
    """The identifier's creation moment, from the minutes the envelope
    carries, as an aware UTC datetime. Read through the package's own
    private helper rather than a public accessor, because the whole minute
    the envelope holds is what picks the signing key and a caller has no
    use for the wire form."""
    return DATE_EPOCH + timedelta(minutes=_date_minutes(fod_id))


def _payload_length_valid(fod_id: FodId) -> bool:
    """Whether the payload is at least the base length for its type, being
    five header bytes plus a 32 byte match key, or 16 for a Random
    identifier. Beyond the base come the Terms byte and then a creator
    context section, whose exact lengths belong to the cloud, so any
    longer payload is accepted here. The base does not include the Terms,
    because a payload ending at the match key carries no byte for it and
    reads as terms that are not stated."""
    match_key_length = _layout.GUID_LENGTH if fod_id.type is IdType.RANDOM \
        else _layout.MATCH_KEY_LENGTH
    return len(fod_id.payload) >= _layout.HEADER_LENGTH + match_key_length


def _moment_of(value: Any) -> Optional[datetime]:
    """An ISO 8601 date and time from a key list entry, or ``None`` where
    the value is not one."""
    if not isinstance(value, str):
        return None
    try:
        return parse_iso8601(value)
    except ValueError:
        return None


def _format_iso8601(moment: datetime) -> str:
    """The moment as ISO 8601 UTC, with the microseconds only where there
    are any. A start read from the cloud's seven fractional digits keeps
    the first six, so the moment written is never after the cloud's own and
    a filter on it still lists the entry it came from."""
    moment = moment.astimezone(timezone.utc)
    fraction = ".{0:06d}".format(moment.microsecond) \
        if moment.microsecond else ""
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + fraction + "Z"


def _started_by(keys: List[PublicKeyEntry],
                at: datetime) -> Optional[datetime]:
    """The start of the newest key held that starts at or before the
    moment, whatever its end, or of the oldest key where none has started
    by then. ``None`` for an empty list."""
    started = [key.starts_at for key in keys if key.starts_at <= at]
    if started:
        return max(started)
    return min((key.starts_at for key in keys), default=None)


def _merge(held: List[PublicKeyEntry],
           answer: List[PublicKeyEntry]) -> List[PublicKeyEntry]:
    """The keys held with an answer merged in by start, oldest first. An
    entry in the answer replaces the held entry with the same start,
    because a later answer may carry an end the held copy lacks, or an
    earlier end where the key was replaced. No held entry is dropped,
    because 51Dids made long ago verify against the keys of their own
    periods."""
    by_start = {key.starts_at: key for key in held}
    for key in answer:
        by_start[key.starts_at] = key
    return sorted(by_start.values(), key=lambda key: key.starts_at)


def _covers(keys: List[PublicKeyEntry], date: datetime) -> bool:
    """Whether the keys held, oldest first, answer the date without a
    fetch. They cover every date more than the boundary tolerance before
    the newest key's end, or before its start where the cloud sent no end,
    because a key without an end is in force until a start not yet
    known."""
    if not keys:
        return False
    newest = keys[-1]
    end = newest.ends_at if newest.ends_at is not None \
        else newest.starts_at
    return date + _BOUNDARY_TOLERANCE < end


def _in_force_at(keys: List[PublicKeyEntry],
                 at: datetime) -> Optional[PublicKeyEntry]:
    """The entry in force at the moment, being the newest whose start has
    passed, or ``None`` when the moment precedes every entry or that entry
    has ended by then."""
    best = None
    for key in keys:
        if key.starts_at > at:
            continue
        if best is None or key.starts_at > best.starts_at:
            best = key
    if best is not None and best.ends_at is not None \
            and at >= best.ends_at:
        return None
    return best


def _verified_by_any(fod_id: FodId, keys: List[PublicKeyEntry]) -> bool:
    return any(fod_id.verify(key.public_key) for key in keys)


def _candidates_for_date(keys: List[PublicKeyEntry],
                         at: datetime) -> List[PublicKeyEntry]:
    """The entries that may have signed something created at the moment,
    best first: the entry in force, then the entry in force a tolerance
    earlier and the entry in force a tolerance later where those differ.
    Empty where no key held was in force at any of those moments, which is
    answered as no key rather than as a failed signature."""
    candidates: List[PublicKeyEntry] = []

    def add(entry: Optional[PublicKeyEntry]) -> None:
        if entry is not None and all(c is not entry for c in candidates):
            candidates.append(entry)

    add(_in_force_at(keys, at))
    add(_in_force_at(keys, at - _BOUNDARY_TOLERANCE))
    add(_in_force_at(keys, at + _BOUNDARY_TOLERANCE))
    return candidates

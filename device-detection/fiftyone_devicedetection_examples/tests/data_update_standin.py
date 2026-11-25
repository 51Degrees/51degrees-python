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
A stand-in for the Distributor on this machine, so a test of the data file
update example never reaches the Distributor and needs no real licence key.

It answers as the Distributor does for a licence key that holds several
products, whatever key it is sent:

- a request that names no product gets 300 with the list of products, and a
  Location header naming the first
- a request for a product not on the list gets 403
- a request for a product on the list gets the data file to serve, gzipped
  and with the MD5 hash of what is sent as lower case hexadecimal, unless the
  request's If-Modified-Since is not earlier than the file's published date,
  when it gets 304

Every request is recorded with the product it named and the status it got.
"""

import functools
import gzip
import hashlib
import http.server
import json
import shutil
import struct
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from unittest import mock
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

import requests

# Where the published date starts in the header of a Hash data file: a 16
# bit year, little endian, then a byte each for the month and the day.
PUBLISHED_OFFSET = 66

# The address the examples ask for an update, which only the stand-in
# answers while a test runs.
DISTRIBUTOR_HOST = "distributor.51degrees.com"

NOT_OFFERED = ('{"Error":"The license key provided does not contain the '
               'requested product."}')

SEVERAL_PRODUCTS = ("There are multiple products associated with this "
                    "license key. Please use the URI returned in the "
                    "Location header.")


def read_published(path):
    """The published date in a data file's header."""
    with open(path, "rb") as file:
        file.seek(PUBLISHED_OFFSET)
        year, month, day = struct.unpack("<hBB", file.read(4))
    return datetime(year, month, day, tzinfo=timezone.utc)


def write_published(path, date):
    """Sets the published date in a data file's header, so a copy of a data
    file can stand for a newer one."""
    with open(path, "r+b") as file:
        file.seek(PUBLISHED_OFFSET)
        file.write(struct.pack("<hBB", date.year, date.month, date.day))


def newer_copy(source, target):
    """Copies the data file at source to target, published tomorrow, and
    gives that date. Tomorrow is later than any If-Modified-Since the
    request can carry, which is the file's published date or, before an
    engine has loaded it, the time the file was last modified."""
    shutil.copyfile(source, target)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    date = datetime(tomorrow.year, tomorrow.month, tomorrow.day,
                    tzinfo=timezone.utc)
    write_published(target, date)
    return date


def product_of(query):
    """The Product parameter of a query, matched whatever its case, or None
    when there is none or it is empty."""
    for name, value in parse_qsl(query, keep_blank_values=True):
        if name.lower() == "product":
            return value or None
    return None


def with_product(url, product):
    """The URL with Product set to the product, as each URI the Distributor
    lists is."""
    parts = urlsplit(url)
    kept = [part for part in parts.query.split("&")
            if part and not part.lower().startswith("product=")]
    kept.append("Product=" + quote(product, safe=""))
    return urlunsplit(parts._replace(query="&".join(kept)))


class StandIn:
    """The stand-in's answers and the requests it received."""

    def __init__(self, products, data_file):
        self.products = list(products)
        self.requests = []
        self._lock = threading.Lock()
        with open(data_file, "rb") as file:
            self.compressed = gzip.compress(file.read())
        self.md5 = hashlib.md5(self.compressed).hexdigest()
        self.published = read_published(data_file)
        self.url = None

    def record(self, product, status):
        with self._lock:
            self.requests.append((product, status))

    def not_modified(self, since):
        if not since:
            return False
        try:
            date = parsedate_to_datetime(since)
        except (TypeError, ValueError):
            return False
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date >= self.published


class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, stand_in, *args, **kwargs):
        self.stand_in = stand_in
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        stand_in = self.stand_in
        product = product_of(urlsplit(self.path).query)
        requested = stand_in.url.split("/api/")[0] + self.path
        if product is None:
            uris = [with_product(requested, offered)
                    for offered in stand_in.products]
            stand_in.record(None, 300)
            self.answer(300, json.dumps({
                "AvailableUris": uris,
                "Error": SEVERAL_PRODUCTS,
            }).encode(), "application/json", {"Location": uris[0]})
        elif product.lower() not in (p.lower() for p in stand_in.products):
            stand_in.record(product, 403)
            self.answer(403, NOT_OFFERED.encode(), "application/json")
        elif stand_in.not_modified(self.headers.get("If-Modified-Since")):
            stand_in.record(product, 304)
            self.send_response(304)
            self.end_headers()
        else:
            stand_in.record(product, 200)
            self.answer(200, stand_in.compressed, "application/octet-stream",
                        {"Content-MD5": stand_in.md5})

    def answer(self, status, body, content_type, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def serving(products, data_file):
    """Serves the data file as the Distributor would for a licence key that
    holds the products, and sends every request the data file update service
    makes to the Distributor to it instead. Gives the stand-in, whose
    requests a test checks."""
    stand_in = StandIn(products, data_file)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, stand_in))
    stand_in.url = (f"http://127.0.0.1:{server.server_address[1]}"
                    "/api/v2/download")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    real_get = requests.get

    def fake_get(url, *args, **kwargs):
        parts = urlsplit(url)
        if parts.hostname == DISTRIBUTOR_HOST:
            url = stand_in.url + ("?" + parts.query if parts.query else "")
        return real_get(url, *args, **kwargs)

    try:
        with mock.patch.object(requests, "get", fake_get):
            yield stand_in
    finally:
        server.shutdown()
        server.server_close()

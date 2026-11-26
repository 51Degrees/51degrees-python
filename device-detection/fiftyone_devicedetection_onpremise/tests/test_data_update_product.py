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

"""The data file names the Distributor's product for the data file in use,
which the data file update service asks for when the license key holds
several products. Once the engine has loaded the data file, the product is
the engine's. Before that it is read from the header of the data file at the
configured location."""

import functools
import http.server
import json
import os
import shutil
import tempfile
import threading
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlsplit

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_devicedetection_onpremise.devicedetection_datafile import \
    DeviceDetectionDataFile
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import \
    DeviceDetectionOnPremise

# The free Lite data file, which the build fetches for the tests. Its tier
# is Lite, so its product is V4Lite.
LITE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cxx",
    "data", "device-detection", "51Degrees-LiteV4.1.hash")
LITE_PRODUCT = "V4Lite"

# A made-up licence key, which is all the stand-in below needs.
MADE_UP_KEY = "MADE-UP-LICENCE-KEY"


def data_file(flow_element, path="not-there.hash"):
    """A data file of the flow element, at the path."""
    return DeviceDetectionDataFile(
        flow_element=flow_element, identifier="HashV41",
        path=path,
        update_url_params={"base_url": "https://example.com/update"})


def loaded(tier):
    """Stands in for an engine that has loaded a data file of the tier."""
    return SimpleNamespace(engine=SimpleNamespace(getProduct=lambda: tier))


class DataUpdateProductTests(unittest.TestCase):

    def test_the_product_is_named_from_the_tier_of_the_data_file(self):
        for tier, product in (
                ("TAC", "V4TAC"),
                ("Enterprise", "V4Enterprise"),
                ("V4TAC", "V4TAC")):
            with self.subTest(tier):
                self.assertEqual(
                    product,
                    data_file(loaded(tier)).get_data_update_product())

    def test_no_product_is_named_without_a_data_file_to_read(self):
        # The update on start-up runs before the engine is built, and a
        # closed engine holds none, so the product is read from the file,
        # and there is no file at the path. An engine that has loaded a
        # file with no tier names no product either.
        for name, flow_element in (
                ("not built", SimpleNamespace()),
                ("closed", SimpleNamespace(engine=None)),
                ("no tier", loaded(""))):
            with self.subTest(name):
                self.assertIsNone(
                    data_file(flow_element).get_data_update_product())

    def test_no_product_is_named_from_a_file_that_is_not_a_data_file(self):
        self.assertIsNone(
            data_file(SimpleNamespace(), path=os.path.abspath(__file__))
            .get_data_update_product())


@unittest.skipUnless(
    os.path.isfile(LITE),
    "No Lite data file at '%s'. CI's fetch-assets script puts it in place."
    % LITE)
class ProductFromFileTests(unittest.TestCase):

    def test_the_product_is_read_from_the_file_before_it_is_loaded(self):
        for name, flow_element in (
                ("not built", SimpleNamespace()),
                ("closed", SimpleNamespace(engine=None))):
            with self.subTest(name):
                self.assertEqual(
                    LITE_PRODUCT,
                    data_file(flow_element, path=LITE)
                    .get_data_update_product())

    def test_the_product_of_a_loaded_engine_is_used_over_the_file(self):
        self.assertEqual(
            "V4TAC",
            data_file(loaded("TAC"), path=LITE).get_data_update_product())

    def test_the_product_of_the_file_is_the_product_of_its_engine(self):
        engine = DeviceDetectionOnPremise(
            data_file_path=LITE, licence_keys="", auto_update=False,
            performance_profile="LowMemory")
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        self.assertEqual(LITE_PRODUCT, "V4" + engine.engine.getProduct())
        self.assertEqual(
            LITE_PRODUCT,
            data_file(SimpleNamespace(), path=LITE).get_data_update_product())


class StandIn(http.server.BaseHTTPRequestHandler):
    """Answers as the Distributor does for a licence key that holds the
    products, whatever key it is sent. A request that names no product gets
    300 and the list of products, a product on the list gets 304, as there
    is nothing newer, and any other product gets 403. Each request is
    recorded with the product it named and the status it got."""

    def __init__(self, products, requests, *args, **kwargs):
        self.products = products
        self.requests = requests
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        query = urlsplit(self.path).query
        product = next((value for name, value in parse_qsl(query)
                        if name.lower() == "product"), None)
        if not product:
            base = "http://%s:%d%s" % (
                self.server.server_address[0], self.server.server_address[1],
                self.path)
            uris = [base + "&Product=" + offered for offered in self.products]
            body = json.dumps({"AvailableUris": uris}).encode()
            status = 300
        elif product in self.products:
            body = b""
            status = 304
        else:
            body = b'{"Error":"Not offered"}'
            status = 403
        self.requests.append((product or None, status))
        self.send_response(status)
        if status == 300:
            self.send_header("Location", uris[0])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(test, products):
    """Starts the stand-in for the test, offering the products, and gives
    its URL and the list its requests are recorded in."""
    requests = []
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(StandIn, products, requests))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    test.addCleanup(server.server_close)
    test.addCleanup(server.shutdown)
    url = "http://127.0.0.1:%d/api/v2/download" % server.server_address[1]
    return url, requests


@unittest.skipUnless(
    os.path.isfile(LITE),
    "No Lite data file at '%s'. CI's fetch-assets script puts it in place."
    % LITE)
class UpdateOnStartUpProductTests(unittest.TestCase):
    """The update on start-up, with no product configured, runs before the
    engine has loaded the data file, so it asks for the product the header
    of the data file names."""

    def start(self, products, product=None):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "51Degrees-LiteV4.1.hash")
        shutil.copyfile(LITE, path)
        url, requests = serve(self, products)
        engine = DeviceDetectionOnPremise(
            data_file_path=path, licence_keys=MADE_UP_KEY,
            auto_update=False, update_on_start=True,
            file_system_watcher=False,
            performance_profile="LowMemory", data_update_url=url,
            data_update_product_type=product)
        pipeline = PipelineBuilder().add(engine).build()
        self.addCleanup(pipeline.close)
        return requests

    def test_the_update_on_start_up_asks_for_the_product_of_the_file(self):
        requests = self.start(("V4TAC", LITE_PRODUCT))
        self.assertEqual([(None, 300), (LITE_PRODUCT, 304)], requests)

    def test_a_configured_product_is_asked_for_in_place_of_the_file(self):
        requests = self.start(("V4TAC", LITE_PRODUCT), "V4TAC")
        self.assertEqual([("V4TAC", 304)], requests)


def formatted(product):
    """The update URL the URL formatter writes for a data file that is
    configured with the product."""
    return DeviceDetectionDataFile(
        flow_element=SimpleNamespace(), identifier="HashV41",
        path="not-read.hash", data_update_use_url_formatter=True,
        update_url_params={
            "base_url": "https://example.com/update",
            "type": "HashV41",
            "license_keys": "ABCDEFGHIJKL",
            "product": product}).get_update_url()


# A product is named in the update URL only when one is configured. Every
# request is made to that URL, so with a product configured every request
# names it, the first included, and with none configured the first request
# has no Product parameter at all.
class ConfiguredProductTests(unittest.TestCase):

    def test_a_configured_product_is_named_in_the_update_url(self):
        self.assertEqual(
            "https://example.com/update?Type=HashV41&"
            "licenseKeys=ABCDEFGHIJKL&Product=V4TAC",
            formatted("V4TAC"))

    def test_no_product_is_named_when_none_is_configured(self):
        for name, product in (("none", None), ("empty", "")):
            with self.subTest(name):
                url = formatted(product)
                self.assertEqual(
                    "https://example.com/update?Type=HashV41&"
                    "licenseKeys=ABCDEFGHIJKL", url)
                self.assertNotIn("product", url.lower())


if __name__ == "__main__":
    unittest.main()

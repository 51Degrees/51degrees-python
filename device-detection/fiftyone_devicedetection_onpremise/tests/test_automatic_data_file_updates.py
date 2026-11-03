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
import hashlib
import os
import threading
import time
import unittest
import gzip
import shutil
import requests
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService
from flask import Flask, send_from_directory, make_response, request

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_onpremise.devicedetection_datafile import DeviceDetectionDataFile
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import \
    DeviceDetectionOnPremisePipelineBuilder

data_file = ExampleUtils.find_file("51Degrees-LiteV4.1.hash")
hash_file_path = data_file
fixtures_path="tests/fixtures"
archive_file_path = f"{fixtures_path}/51Degrees-LiteV4.1.gz"


class DeviceDetectionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.port = 5689
        cls._run_web_server(
            cls.port,
            cls._init_hash_file_archive()
        )

        time.sleep(2)

    @classmethod
    def tearDownClass(cls) -> None:
        requests.get(f"http://127.0.0.1:{cls.port}/shutdown")
        cls.clear()

    def test_on_premise_data_update_url(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            data_update_verify_md5=False,
            data_update_url=f"http://127.0.0.1:{self.port}"
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertFalse(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_old_property_data_file_update_base_url(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            data_update_verify_md5=False,
            data_file_update_base_url=f"http://127.0.0.1:{self.port}"
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertFalse(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_url_config(self):
        config = self._build_pipeline_config(
            {
                "data_file_path": f"{data_file}",
                "usage_sharing": False,
                "licence_keys": "test",
                "update_on_start": True,
                "data_update_verify_md5": False,
                "data_update_url": f"http://127.0.0.1:{self.port}"
            }
        )

        pipeline = PipelineBuilder().build_from_configuration(config)
        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertFalse(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_config_old_property_data_file_update_base_url(self):
        config = self._build_pipeline_config(
            {
                "data_file_path": f"{data_file}",
                "usage_sharing": False,
                "licence_keys": "test",
                "update_on_start": True,
                "data_update_verify_md5": False,
                "data_file_update_base_url": f"http://127.0.0.1:{self.port}"
            }
        )

        pipeline = PipelineBuilder().build_from_configuration(config)
        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertFalse(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_verify_md5(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            data_update_verify_md5=True,
            data_update_url=f"http://127.0.0.1:{self.port}/md5"
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertTrue(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_verify_md5_old_property(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            verify_md5=True,
            data_update_url=f"http://127.0.0.1:{self.port}/md5"
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertTrue(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_verify_md5_config(self):
        config = self._build_pipeline_config(
            {
                "data_file_path": f"{data_file}",
                "usage_sharing": False,
                "licence_keys": "test",
                "update_on_start": True,
                "data_update_verify_md5": True,
                "data_update_url": f"http://127.0.0.1:{self.port}/md5"
            }
        )

        pipeline = PipelineBuilder().build_from_configuration(config)
        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertTrue(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_verify_md5_config_old_property(self):
        config = self._build_pipeline_config(
            {
                "data_file_path": f"{data_file}",
                "usage_sharing": False,
                "licence_keys": "test",
                "update_on_start": True,
                "verify_md5": True,
                "data_update_url": f"http://127.0.0.1:{self.port}/md5"
            }
        )

        pipeline = PipelineBuilder().build_from_configuration(config)
        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertTrue(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_use_url_formatter(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            data_update_verify_md5=False,
            data_update_url=f"http://127.0.0.1:{self.port}/",
            data_update_use_url_formatter=False
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self._assertNotSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_use_url_formatter_config(self):
        config = self._build_pipeline_config(
            {
                "data_file_path": f"{data_file}",
                "usage_sharing": False,
                "licence_keys": "test",
                "update_on_start": True,
                "data_update_verify_md5": False,
                "data_update_url": f"http://127.0.0.1:{self.port}",
                "data_update_use_url_formatter": False
            }
        )

        pipeline = PipelineBuilder().build_from_configuration(config)
        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self._assertNotSignedUrl(flow_element_data_file.get_update_url())

    def test_on_premise_data_update_status_rate_limit(self):
        pipeline = DeviceDetectionOnPremisePipelineBuilder(
            data_file_path=data_file,
            usage_sharing=False,
            licence_keys="test",
            update_on_start=True,
            verify_md5=True,
            data_update_url=f"http://127.0.0.1:{self.port}/status/429"
        ).build()

        pipeline.create_flowdata().process()

        flow_element_data_file = pipeline.flow_elements[0].data_file
        self.assertIsInstance(flow_element_data_file, DeviceDetectionDataFile)
        self.assertTrue(flow_element_data_file.verify_md5)
        self._assertSignedUrl(flow_element_data_file.get_update_url())

    def _build_pipeline_config(self, parameters):
        return {
            "PipelineOptions": {
                "Elements": [
                    {
                        "elementName": "DeviceDetectionOnPremise",
                        "elementPath": "fiftyone_devicedetection_onpremise.devicedetection_onpremise",
                        "elementParameters": parameters
                    }
                ]
            }
        }

    def _assertSignedUrl(self, url):
        self.assertIn(f"http://127.0.0.1:{self.port}", url)
        self.assertIn("Type", url)
        self.assertIn("licenseKeys", url)

    def _assertNotSignedUrl(self, url):
        self.assertIn(f"http://127.0.0.1:{self.port}", url)
        self.assertNotIn("Type", url)
        self.assertNotIn("licenseKeys", url)


    @staticmethod
    def _run_web_server(port, file_md5):
        def run():
            app = Flask(__name__)

            @app.route("/")
            def root():
                return send_from_directory("fixtures", "51Degrees-LiteV4.1.gz", as_attachment=True)

            @app.route("/md5")
            def md5():
                response = make_response(
                    send_from_directory("fixtures", "51Degrees-LiteV4.1.gz", as_attachment=True)
                )
                response.headers["content-md5"] = file_md5

                return response

            @app.route("/status/<status>")
            def response_status(status):
                return "Record not found", status

            @app.route("/shutdown")
            def shutdown():
                from flask import request
                request.environ["werkzeug.server.shutdown"]()
                return "OK", 200

            app.run(host="127.0.0.1", port=port)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    @staticmethod
    def _init_hash_file_archive():
        os.makedirs(fixtures_path)
        with open(hash_file_path, "rb") as f_in:
            with gzip.open(archive_file_path, "wb", compresslevel=1) as f_out:
                shutil.copyfileobj(f_in, f_out)

        return hashlib.md5(open(archive_file_path, "rb").read()).hexdigest()

    @staticmethod
    def clear():
        os.remove(archive_file_path)
        os.rmdir(fixtures_path)

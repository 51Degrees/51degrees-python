
"""
A licence key is shown as its last 4 characters, each hidden character
replaced by an asterisk, wherever a key or a URL that carries one is logged or
raised. A key of 4 or fewer characters is replaced entirely.
"""

import unittest
from unittest import mock

import requests

from fiftyone_pipeline_core.keymask import mask_licence_key
from fiftyone_pipeline_core.keymask import mask_licence_keys_in_text
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService

from .test_datafile_update_service import RecordingPipeline

KEY = "ABCDEFGHIJKL"
URL = "https://example.com/update?Type=Hash&licenseKeys=" + KEY + "&Product=V4"
MASKED_URL = (
    "https://example.com/update?Type=Hash&licenseKeys=********IJKL"
    "&Product=V4")


class MaskTests(unittest.TestCase):

    def test_last_four_characters_are_shown(self):
        self.assertEqual("********IJKL", mask_licence_key(KEY))
        self.assertEqual("*2345", mask_licence_key("12345"))

    def test_four_or_fewer_characters_are_replaced_entirely(self):
        self.assertEqual("****", mask_licence_key("abcd"))
        self.assertEqual("***", mask_licence_key("abc"))
        self.assertEqual("*", mask_licence_key("a"))
        self.assertEqual("", mask_licence_key(""))

    def test_a_key_in_a_url_is_masked(self):
        self.assertEqual(MASKED_URL, mask_licence_keys_in_text(URL))

    def test_every_key_of_a_list_is_masked(self):
        for separator in ("|", "%7C", "%7c"):
            text = "x?licenseKeys=AAAAAAAA" + separator + "BBBBB&a=b"
            self.assertEqual(
                "x?licenseKeys=****AAAA" + separator + "*BBBB&a=b",
                mask_licence_keys_in_text(text), separator)

    def test_other_spellings_of_the_parameter_are_masked(self):
        for name in ("licenseKey", "LicenceKeys", "licence", "license_keys"):
            self.assertEqual(
                "u?" + name + "=********IJKL",
                mask_licence_keys_in_text("u?" + name + "=" + KEY), name)

    def test_text_without_a_key_is_unchanged(self):
        text = "https://example.com/update?Type=Hash&Product=V4"
        self.assertEqual(text, mask_licence_keys_in_text(text))


class StandInDataFile:

    def __init__(self):
        self.identifier = "id"
        self.update_on_start = False
        self.auto_update = False
        self.file_system_watcher = False
        self.updating = False
        self.verify_if_modified_since = False
        self.verify_md5 = False
        self.decompress = False
        self.download = False
        self.create_temp_copy = False
        self.data = b"old"

        class Engine:
            datakey = "device"
        self.flow_element = Engine()

    def get_update_url(self):
        return URL

    def refresh(self):
        pass


def answer(status):
    reply = mock.Mock()
    reply.status_code = status
    reply.content = b"x"
    reply.headers = {}
    return reply


class UpdateServiceLogTests(unittest.TestCase):

    def update(self, reply):
        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        with mock.patch.object(requests, "get", lambda *a, **k: reply):
            service.update_data_file(StandInDataFile())
        return pipeline.logs

    def test_no_message_holds_the_key(self):
        for status in (304, 403, 429, 500):
            logs = self.update(answer(status))
            self.assertTrue(logs, status)
            for level, message in logs:
                self.assertNotIn(KEY, message, status)
                self.assertNotIn("ABCDEFGH", message, status)

    def test_the_masked_url_is_in_the_message(self):
        logs = self.update(answer(403))
        self.assertTrue(any(MASKED_URL in message for level, message in logs),
                        logs)

    def test_an_error_raised_by_the_request_does_not_hold_the_key(self):
        def fail(*args, **kwargs):
            raise requests.ConnectionError("failed for url: " + URL)

        service = DataFileUpdateService(RecordingPipeline())
        with mock.patch.object(requests, "get", fail):
            with self.assertRaises(requests.RequestException) as caught:
                service.update_data_file(StandInDataFile())
        self.assertNotIn(KEY, str(caught.exception))
        self.assertIn(MASKED_URL, str(caught.exception))


if __name__ == "__main__":
    unittest.main()

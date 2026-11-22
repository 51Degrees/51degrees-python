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

"""
Every character of a licence key is replaced by an asterisk wherever a key or
a URL that carries one is logged or raised.
"""

import re
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
    "https://example.com/update?Type=Hash&licenseKeys=************"
    "&Product=V4")


class MaskTests(unittest.TestCase):

    def test_every_character_is_replaced(self):
        self.assertEqual("************", mask_licence_key(KEY))
        self.assertEqual("*****", mask_licence_key("12345"))
        self.assertEqual("****", mask_licence_key("abcd"))
        self.assertEqual("***", mask_licence_key("abc"))
        self.assertEqual("*", mask_licence_key("a"))
        self.assertEqual("", mask_licence_key(""))

    def test_visible_characters_is_deprecated_and_zero(self):
        with self.assertWarns(DeprecationWarning):
            from fiftyone_pipeline_core.keymask import VISIBLE_CHARACTERS
        self.assertEqual(0, VISIBLE_CHARACTERS)

    def test_a_key_in_a_url_is_masked(self):
        self.assertEqual(MASKED_URL, mask_licence_keys_in_text(URL))

    def test_every_key_of_a_list_is_masked(self):
        for separator in ("|", "%7C", "%7c"):
            text = "x?licenseKeys=AAAAAAAA" + separator + "BBBBB&a=b"
            self.assertEqual(
                "x?licenseKeys=********" + separator + "*****&a=b",
                mask_licence_keys_in_text(text), separator)

    def test_other_spellings_of_the_parameter_are_masked(self):
        for name in ("licenseKey", "LicenceKeys", "licence", "license_keys"):
            self.assertEqual(
                "u?" + name + "=************",
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
    """Update polling logs a failed check, so each check here is a polled
    one."""

    def update(self, reply):
        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        with mock.patch.object(requests, "get", lambda *a, **k: reply):
            service.async_update_data_file(StandInDataFile()).join()
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

    def test_a_failed_request_logs_only_the_masked_key(self):
        # The message of the request's error names the URL.
        def fail(*args, **kwargs):
            raise requests.ConnectionError("failed for url: " + URL)

        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        with mock.patch.object(requests, "get", fail):
            service.async_update_data_file(StandInDataFile()).join()
        self.assertTrue(pipeline.logs)
        for level, message in pipeline.logs:
            self.assertNotIn(KEY, message)
        self.assertTrue(any(MASKED_URL in message
                            for level, message in pipeline.logs),
                        pipeline.logs)

    def test_a_callback_error_logs_only_the_masked_key(self):
        # A callback's error is written into the log entry, and a callback
        # that passes on a request error carries the update URL with it.
        def fails(status, data_file):
            raise requests.ConnectionError("failed for url: " + URL)

        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        service.on_complete(fails)
        with mock.patch.object(requests, "get", lambda *a, **k: answer(304)):
            service.async_update_data_file(StandInDataFile()).join()
        self.assertTrue(pipeline.logs)
        for level, message in pipeline.logs:
            self.assertNotIn(KEY, message)
        self.assertTrue(any(MASKED_URL in message
                            for level, message in pipeline.logs),
                        pipeline.logs)


# An obviously fake key, used only by these tests.
FAKE_KEY = "FAKE0KEY1FOR2TESTS3ONLY4"
FAKE_URL = ("https://example.com/update?Type=Hash&licenseKeys=" + FAKE_KEY +
            "&Product=V4")
KEY_VALUE = re.compile(r"licenseKeys=([^&'\s]*)")


class FakeKeyDataFile(StandInDataFile):

    def get_update_url(self):
        return FAKE_URL


class NoCharacterOfTheKeyIsLoggedTests(unittest.TestCase):
    """The update service logs the update URL with every character of the
    licence key masked."""

    def assertNoCharacterOfTheKey(self, logs):
        self.assertTrue(logs)
        for level, message in logs:
            self.assertNotIn(FAKE_KEY, message)
        values = [value for level, message in logs
                  for value in KEY_VALUE.findall(message)]
        self.assertTrue(values, logs)
        for value in values:
            self.assertFalse(set(value) & set(FAKE_KEY), value)

    def test_each_answer_logs_no_character_of_the_key(self):
        for status in (304, 403, 429, 500):
            pipeline = RecordingPipeline()
            service = DataFileUpdateService(pipeline)
            with mock.patch.object(
                    requests, "get", lambda *a, **k: answer(status)):
                service.async_update_data_file(FakeKeyDataFile()).join()
            with self.subTest(status):
                self.assertNoCharacterOfTheKey(pipeline.logs)

    def test_a_failed_request_logs_no_character_of_the_key(self):
        # The message of the request's error names the URL.
        def fail(*args, **kwargs):
            raise requests.ConnectionError("failed for url: " + FAKE_URL)

        pipeline = RecordingPipeline()
        service = DataFileUpdateService(pipeline)
        with mock.patch.object(requests, "get", fail):
            service.async_update_data_file(FakeKeyDataFile()).join()
        self.assertNoCharacterOfTheKey(pipeline.logs)


if __name__ == "__main__":
    unittest.main()

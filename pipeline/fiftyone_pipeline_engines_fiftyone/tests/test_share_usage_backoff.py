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

import unittest

from fiftyone_pipeline_engines_fiftyone.share_usage_backoff import \
    ShareUsageBackOff


def create(failures=3, initial=2, maximum=5):
    """!
    Three failures within a ten second window start a two second pause,
    rising by two each time up to five.
    """
    return ShareUsageBackOff(failures, 10, initial, maximum, 2)


class ShareUsageBackOffTests(unittest.TestCase):
    """!
    The rules that decide when usage sharing may send after failed sends,
    with each test setting the time.
    """

    def test_pauses_after_failures_within_window(self):
        backoff = create()

        self.assertEqual(backoff.failed(0), 0)
        self.assertEqual(backoff.failed(1), 0)
        self.assertEqual(backoff.remaining(1), 0,
            "Sending paused before enough sends failed.")
        self.assertFalse(backoff.backing_off)

        self.assertEqual(backoff.failed(2), 2)
        self.assertTrue(backoff.backing_off)
        self.assertEqual(backoff.remaining(3), 1)
        self.assertEqual(backoff.remaining(4), 0)

    def test_failures_outside_window_do_not_count(self):
        backoff = create()

        backoff.failed(0)
        backoff.failed(1)

        self.assertEqual(backoff.failed(11.5), 0,
            "Failures older than the window were counted.")
        self.assertFalse(backoff.backing_off)

    def test_successes_between_failures_do_not_reset(self):
        """!
        The window counts failures, not failures in a row, so a high
        failure rate pauses sending even when some sends succeed.
        """
        backoff = create()

        backoff.failed(0)
        self.assertFalse(backoff.succeeded())
        backoff.failed(1)
        self.assertFalse(backoff.succeeded())

        self.assertEqual(backoff.failed(2), 2)

    def test_failed_send_after_pause_multiplies_delay(self):
        backoff = create(failures=1)

        self.assertEqual(backoff.failed(0), 2)
        self.assertEqual(backoff.failed(2), 4)
        self.assertEqual(backoff.failed(6), 5,
            "The delay grew past the maximum.")
        self.assertEqual(backoff.failed(11), 5)
        self.assertEqual(backoff.remaining(11), 5)

    def test_success_ends_back_off(self):
        backoff = create(failures=2)
        backoff.failed(0)
        backoff.failed(1)
        backoff.failed(3)

        self.assertTrue(backoff.succeeded(),
            "A success did not end the back-off.")
        self.assertFalse(backoff.backing_off)
        self.assertEqual(backoff.remaining(4), 0)

        # The next pause needs the full number of failures again, and
        # starts from the initial delay.
        self.assertEqual(backoff.failed(8), 0)
        self.assertEqual(backoff.failed(9), 2)

    def test_maximum_below_initial_limits_first_pause(self):
        backoff = create(failures=1, initial=10, maximum=3)

        self.assertEqual(backoff.failed(0), 3)

    def test_invalid_settings_are_rejected(self):
        for settings in [
                (0, 10, 2, 5, 2),
                (101, 10, 2, 5, 2),
                (1, 0, 2, 5, 2),
                (1, 10, 0, 5, 2),
                (1, 10, float("nan"), 5, 2),
                (1, 10, 2, 0, 2),
                (1, 10, 2, 5, 0.5)]:
            with self.assertRaises(ValueError, msg=str(settings)):
                ShareUsageBackOff(*settings)

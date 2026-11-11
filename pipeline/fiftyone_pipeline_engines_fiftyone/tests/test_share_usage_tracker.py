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
from unittest import mock

from fiftyone_pipeline_engines_fiftyone.share_usage_tracker import \
    ShareUsageTracker

# The tracker reads the time through this name.
TIME = "fiftyone_pipeline_engines_fiftyone.share_usage_tracker.time.time"

INTERVAL_SECONDS = 60
START = 1000000.0


class ShareUsageTrackerTests(unittest.TestCase):

    def track_at(self, tracker, key, seconds):
        """!
        Track the key with the clock at the given seconds after the start.
        """
        with mock.patch(TIME, return_value=START + seconds):
            return tracker.track(key)

    def share_at(self, tracker, key, seconds):
        """!
        Track the key as the element does, storing the time when it is shared.
        """
        with mock.patch(TIME, return_value=START + seconds):
            shared = tracker.track(key)
            if shared:
                tracker.set_cache_value(key)
            return shared

    def test_repeat_inside_the_interval_is_not_shared(self):
        tracker = ShareUsageTracker(interval=INTERVAL_SECONDS)
        self.assertTrue(self.share_at(tracker, "a", 0))

        self.assertFalse(
            self.track_at(tracker, "a", INTERVAL_SECONDS - 1))

    def test_repeat_at_the_interval_is_shared(self):
        tracker = ShareUsageTracker(interval=INTERVAL_SECONDS)
        self.assertTrue(self.share_at(tracker, "a", 0))

        self.assertTrue(self.track_at(tracker, "a", INTERVAL_SECONDS))

    def test_repeat_after_the_interval_is_shared(self):
        tracker = ShareUsageTracker(interval=INTERVAL_SECONDS)
        self.assertTrue(self.share_at(tracker, "a", 0))

        self.assertTrue(self.track_at(tracker, "a", INTERVAL_SECONDS + 1))

    def test_repeat_inside_the_interval_leaves_the_time(self):
        tracker = ShareUsageTracker(interval=INTERVAL_SECONDS)
        self.assertTrue(self.share_at(tracker, "a", 0))
        self.assertFalse(self.share_at(tracker, "a", 30))

        self.assertTrue(self.track_at(tracker, "a", INTERVAL_SECONDS))


if __name__ == '__main__':
    unittest.main()

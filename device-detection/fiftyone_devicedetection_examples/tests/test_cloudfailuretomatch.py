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
The cloud failure to match example is a script with no main, which does its
work when it is run as a module. The test runs it inside the test process,
as python -m runs it, so the lines it runs are measured with the rest of the
examples.
"""

import io
import os
import runpy
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fiftyone_devicedetection_examples.example_utils import ExampleUtils

from .live_cloud import answered_without, find_resource_key, no_resource_key

MODULE = "fiftyone_devicedetection_examples.cloud.failuretomatch"

NO_KEY = no_resource_key("the device product", "the IsMobile property")

# The example prints this after each User-Agent it asks about, and the answer
# on the next line.
QUESTION = "a mobile device?:"


class CloudFailureToMatchTests(unittest.TestCase):

    def test_runs_as_a_module(self):
        resource_key = find_resource_key()
        if not resource_key:
            self.fail(NO_KEY)

        printed = io.StringIO()
        with mock.patch.dict(
                os.environ,
                {ExampleUtils.RESOURCE_KEY_ENV_VAR: resource_key}), \
                redirect_stdout(printed):
            runpy.run_module(MODULE, run_name="__main__")

        output = printed.getvalue()
        lines = output.splitlines()
        self.assertNotIn(
            ExampleUtils.get_missing_resource_key_message(), output)
        questions = [index for index, line in enumerate(lines)
                     if QUESTION in line]
        self.assertEqual(2, len(questions), output)

        # The first User-Agent is an iPhone's.
        iphone = lines[questions[0] + 1]
        self.assertEqual(
            "True", iphone,
            answered_without("IsMobile for an iPhone", iphone,
                             "the device product"))

        # The second is not a User-Agent at all, so the answer is a value or
        # the reason there is none, and either one is printed.
        self.assertTrue(lines[questions[1] + 1].strip(), output)


if __name__ == "__main__":
    unittest.main()

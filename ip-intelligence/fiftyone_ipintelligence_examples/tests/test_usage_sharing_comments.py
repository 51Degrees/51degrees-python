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

"""Each on-premise console example that turns usage sharing off says that
production deployments should turn it on, as
ip-intelligence-specification/required-examples.md line 241 asks."""

import os
import re
import unittest

ONPREMISE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src",
    "fiftyone_ipintelligence_examples", "onpremise")

# The lines before a usage_sharing setting that the comment must be among.
LINES_BEFORE = 4


class UsageSharingCommentTests(unittest.TestCase):

    def test_each_example_that_turns_sharing_off_says_why_production_should_not(self):
        found = 0
        for name in sorted(os.listdir(ONPREMISE)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(ONPREMISE, name), encoding="utf-8") as file:
                lines = file.read().splitlines()
            for index, line in enumerate(lines):
                if re.search(r"usage_sharing\s*=\s*False", line):
                    found += 1
                    before = " ".join(
                        lines[max(0, index - LINES_BEFORE):index]).lower()
                    with self.subTest(example=name, line=index + 1):
                        self.assertIn("production", before)
        self.assertGreater(found, 0)


if __name__ == "__main__":
    unittest.main()

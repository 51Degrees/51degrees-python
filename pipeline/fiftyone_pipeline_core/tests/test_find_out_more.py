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
Every example ends with a "Find out more" section, which gives the person
running it links to follow up. The check reads the example's source, so it
needs no network.
"""

import os
import re
import unittest

# The product folder. Each link's utm_content is the path of its file below
# this folder.
PRODUCT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# The example of a custom flow element, a web page that ends with the
# section.
EXAMPLE = os.path.join(
    PRODUCT, "fiftyone_pipeline_core", "examples",
    "client_side_evidence_custom_flow_element.py")

# The name of the section, or of the list that holds its links.
SECTION_NAME = re.compile(r"(?i)find[ _]out[ _]more")

# A 51degrees.com link in the section, which carries a utm_term that starts
# with "find-out-more".
SECTION_LINK = re.compile(
    r"https://51degrees\.com/[^\s\"'<>)]*utm_term=find-out-more[^\s\"'<>)]*")

# This product's folder in the repository, which every section links to.
REPOSITORY = "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"


class FindOutMoreTests(unittest.TestCase):

    def test_the_example_has_a_find_out_more_section(self):
        with open(EXAMPLE, encoding="utf-8") as source:
            text = source.read()
        self.assertRegex(text, SECTION_NAME)
        links = SECTION_LINK.findall(text)
        self.assertTrue(links, "The section has no tagged 51degrees.com link")
        content = os.path.relpath(EXAMPLE, PRODUCT).replace(os.sep, "-")
        for link in links:
            self.assertIn(f"&utm_content={content}&", link)
        self.assertIn(REPOSITORY, text)


if __name__ == "__main__":
    unittest.main()

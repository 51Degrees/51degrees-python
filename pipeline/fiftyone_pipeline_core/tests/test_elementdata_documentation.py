
"""
The documentation of Element Data says it is safe to read from several threads
once the Flow Element that writes it has finished, and is not catered for when
written from several threads or read while another thread writes, as the
thread safety page of the specification requires.
"""

import unittest

from fiftyone_pipeline_core.elementdata import ElementData


class ElementDataDocumentationTests(unittest.TestCase):

    def test_the_documentation_says_what_is_safe_with_threads(self):
        text = " ".join(ElementData.__doc__.split())
        self.assertIn("safe to read from several threads", text)
        self.assertIn("once the Flow Element that writes it has finished", text)
        self.assertIn("not catered for", text)
        self.assertIn("written from several threads", text)
        self.assertIn("read while another thread writes", text)


if __name__ == "__main__":
    unittest.main()


"""
The documentation of Element Data says it is safe to read from several threads
once the Flow Element that writes it has finished, and is not catered for when
written from several threads or read while another thread writes. It also says
that Element Data reading from a results instance, which holds unmanaged
memory, is not safe to use from several threads at once and that the caller is
responsible, as the thread safety page of the specification requires.
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

    def test_the_documentation_says_results_instances_are_the_exception(self):
        text = " ".join(ElementData.__doc__.split())
        self.assertIn("results instance", text)
        self.assertIn("unmanaged memory", text)
        self.assertIn(
            "Multi-threaded access to a results instance is not supported, "
            "for performance reasons", text)
        self.assertIn("caller is responsible for thread-safe access", text)


if __name__ == "__main__":
    unittest.main()

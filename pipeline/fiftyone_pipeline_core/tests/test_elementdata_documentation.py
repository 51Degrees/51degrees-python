
"""
The documentation of Element Data says it is written only by the Flow Element
that provides it, or those that share it, and only while they process, and
that it is then safe to read from several threads. It also says that Element
Data reading from a results instance, which references unmanaged memory, is
not safe to use from several threads at once, takes no lock and leaves the
caller responsible, as the thread safety page of the specification requires.
"""

import unittest

from fiftyone_pipeline_core.elementdata import ElementData


class ElementDataDocumentationTests(unittest.TestCase):

    def test_the_documentation_says_who_writes_and_when(self):
        text = " ".join(ElementData.__doc__.split())
        self.assertIn(
            "written only by the Flow Element that provides it, or by the "
            "Flow Elements that share it, and only while they process", text)
        self.assertIn("safe to read from several threads", text)
        self.assertIn("used by one thread at a time", text)

    def test_the_documentation_says_results_instances_are_the_exception(self):
        text = " ".join(ElementData.__doc__.split())
        self.assertIn("results instance", text)
        self.assertIn("unmanaged memory", text)
        self.assertIn(
            "Multi-threaded access to a results instance is not supported, "
            "for performance reasons", text)
        self.assertIn("takes no lock", text)
        self.assertIn("caller is responsible for thread-safe access", text)


if __name__ == "__main__":
    unittest.main()

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
A results instance is not safe to use from several threads at once and the
caller is responsible for thread-safe access, so SwigData takes no lock and
its documentation says so.
"""

import threading
import unittest

from fiftyone_ipintelligence_onpremise.swig_data import SwigData


# The types of the locks the threading module makes.
LOCK_TYPES = (
    type(threading.Lock()), type(threading.RLock()),
    threading.Condition, threading.Semaphore)


class FakeElement:
    datakey = "ip"
    properties = {}


class SwigDataThreadTests(unittest.TestCase):

    def test_the_documentation_says_the_caller_coordinates_threads(self):
        text = " ".join(SwigData.__doc__.split())
        self.assertIn("unmanaged memory", text)
        self.assertIn(
            "Multi-threaded access to a results instance is not supported, "
            "for performance reasons", text)
        self.assertIn("not safe to use from several threads at once", text)
        self.assertIn("caller is responsible for thread-safe access", text)

    def test_an_instance_holds_no_lock(self):
        data = SwigData(FakeElement(), object())
        locks = [name for name, value in vars(data).items()
                 if isinstance(value, LOCK_TYPES)]
        self.assertEqual([], locks)


if __name__ == "__main__":
    unittest.main()

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
A cloud example has to run with only the cloud packages installed, because
the on-premise package ships as source and needs a C++ toolchain to build.
Someone following a cloud example should not have to build that.

These tests import each cloud example in a separate process with the
on-premise package blocked, so they prove the point whether or not the
on-premise package happens to be installed on the machine running them.
They need no resource key and no network connection.
"""

import subprocess
import sys
import unittest

# The packages a cloud example must not reach for, directly or through
# anything it imports.
BLOCKED = [
    "fiftyone_devicedetection_onpremise",
    "fiftyone_devicedetection",
]

# Every cloud example module. Adding a cloud example means adding it here.
CLOUD_EXAMPLES = [
    "fiftyone_devicedetection_examples.cloud.configurator_console",
    "fiftyone_devicedetection_examples.cloud.failuretomatch",
    "fiftyone_devicedetection_examples.cloud.gettingstarted_console",
    "fiftyone_devicedetection_examples.cloud.metadata_console",
    "fiftyone_devicedetection_examples.cloud.nativemodellookup_console",
    "fiftyone_devicedetection_examples.cloud.taclookup_console",
    "fiftyone_devicedetection_examples.cloud.gettingstarted_web.app",
    "fiftyone_devicedetection_examples.cloud.useragentclienthints_web.app",
]

# Run in a separate process so that a module already imported by another
# test cannot hide the dependency. The finder is placed at the front of
# sys.meta_path, so it is consulted before the ordinary import machinery.
SCRIPT = """
import importlib.abc
import sys

blocked = {blocked!r}


class Blocker(importlib.abc.MetaPathFinder):
    def find_module(self, fullname, path=None):
        return self.find_spec(fullname, path)

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in blocked:
            raise ImportError(
                "'" + fullname + "' must not be needed by a cloud example")
        return None


sys.meta_path.insert(0, Blocker())

import {module}
print("ok")
"""


class CloudExampleImportTests(unittest.TestCase):

    def test_every_cloud_example_imports_without_the_onpremise_package(self):
        for module in CLOUD_EXAMPLES:
            with self.subTest(module=module):
                script = SCRIPT.format(blocked=BLOCKED, module=module)

                result = subprocess.run(
                    [sys.executable, "-c", script],
                    capture_output=True,
                    text=True)

                self.assertEqual(
                    0, result.returncode,
                    f"'{module}' could not be imported with the on-premise "
                    f"packages blocked, so a cloud example needs the "
                    f"on-premise native engine:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()

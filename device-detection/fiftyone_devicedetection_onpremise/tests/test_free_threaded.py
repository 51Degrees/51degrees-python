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
On a free-threaded build of Python, loading the native module turns the GIL
back on, with a RuntimeWarning, because the module does not declare that it
runs without the GIL. A change that loaded it with the GIL still off fails
here. Each check runs in a new interpreter, as this one may have loaded the
module already.
"""

import os
import subprocess
import sys
import sysconfig
import unittest

# The SWIG module, which loads the native module when it is imported.
MODULE = "fiftyone_devicedetection_onpremise.DeviceDetectionHashEngineModule"
NATIVE_MODULE = "_DeviceDetectionHashEngineModule"

FREE_THREADED = sysconfig.get_config_var("Py_GIL_DISABLED") == 1

# Prints whether the GIL is on before and after the import, then the
# warnings the import gave, one to a line.
CHECK = "\n".join([
    "import sys, warnings",
    "warnings.simplefilter('always')",
    "before = sys._is_gil_enabled()",
    "with warnings.catch_warnings(record=True) as caught:",
    "    import " + MODULE,
    "print(before, sys._is_gil_enabled())",
    "for warning in caught:",
    "    print(warning.category.__name__, str(warning.message))",
])


@unittest.skipUnless(FREE_THREADED, "Python is not a free-threaded build")
class FreeThreadedTests(unittest.TestCase):

    def import_in_a_new_interpreter(self):
        env = dict(os.environ)
        # PYTHON_GIL would set the GIL whatever the module declares.
        env.pop("PYTHON_GIL", None)
        result = subprocess.run(
            [sys.executable, "-c", CHECK], env=env, capture_output=True,
            text=True)
        # The new interpreter's own error says why an import failed.
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.splitlines()

    def test_loading_the_native_module_turns_the_gil_on(self):
        lines = self.import_in_a_new_interpreter()
        self.assertEqual("False True", lines[0])

    def test_loading_the_native_module_warns_that_the_gil_is_on(self):
        warnings = self.import_in_a_new_interpreter()[1:]
        self.assertTrue(
            any(line.startswith("RuntimeWarning ")
                and "GIL" in line and NATIVE_MODULE in line
                for line in warnings),
            warnings)


if __name__ == "__main__":
    unittest.main()

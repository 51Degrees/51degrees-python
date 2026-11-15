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
Each function a user calls that raises says in its docstring what it raises,
with an @raise line naming the exception, as exception-handling.md lines 17
to 19 ask. That is the Epytext form the docstrings of this repository use.
"""

import unittest

from fiftyone_pipeline_core.aspectproperty_value import \
    AspectPropertyValue
from fiftyone_pipeline_core.flowdata import FlowData
from fiftyone_pipeline_core.pipeline import Pipeline

# Each function, and the exceptions its docstring has to name.
DOCUMENTED = [
    (FlowData.process, ["Exception"]),
    (FlowData.get, ["Exception"]),
    (FlowData.__getattr__, ["Exception"]),
    (FlowData.__getitem__, ["Exception"]),
    (Pipeline.close, ["Exception"]),
    (Pipeline.element_not_found, ["Exception"]),
    (AspectPropertyValue.value, ["Exception"]),
]


class DocumentedErrorsTests(unittest.TestCase):

    def test_each_function_names_what_it_raises(self):
        for function, names in DOCUMENTED:
            for name in names:
                with self.subTest(function=function.__qualname__, raises=name):
                    self.assertIn(
                        "@raise " + name + ":", function.__doc__ or "")


if __name__ == "__main__":
    unittest.main()

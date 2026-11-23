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
Every FlowElement this package defines is processed, as the thread safety
page of the specification requires. The usage sharing element adds no
ElementData, so a finished FlowData holds none for it, and the FlowData
refuses one being added.
"""

import importlib
import inspect
import pkgutil
import unittest

import fiftyone_pipeline_engines_fiftyone
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

FINISHED = "finished processing"


def defined_flow_elements(package):
    """Every FlowElement class defined in the package's own modules."""
    found = set()
    for module in pkgutil.walk_packages(package.__path__,
                                        package.__name__ + "."):
        loaded = importlib.import_module(module.name)
        for _, cls in inspect.getmembers(loaded, inspect.isclass):
            if (issubclass(cls, FlowElement)
                    and cls.__module__.startswith(package.__name__)):
                found.add(cls)
    return found


class FinishedWritesTests(unittest.TestCase):

    def test_every_flow_element_refuses_writes_once_finished(self):
        # Nothing listens on the discard port, and one record is far short
        # of a package, so nothing is sent.
        usage = ShareUsage(requested_package_size=1000,
                           endpoint="http://127.0.0.1:9")
        pipeline = PipelineBuilder().add(usage).build()
        self.addCleanup(pipeline.close)
        flowdata = pipeline.create_flowdata()
        flowdata.evidence.add("header.user-agent", "a user agent")
        flowdata.process()
        self.assertNotIn(usage.datakey, flowdata.data)
        with self.assertRaises(Exception) as caught:
            flowdata.set_element_data(ElementDataDictionary(usage, {}))
        self.assertIn(FINISHED, str(caught.exception))
        self.assertEqual(
            {ShareUsage},
            defined_flow_elements(fiftyone_pipeline_engines_fiftyone))


if __name__ == "__main__":
    unittest.main()

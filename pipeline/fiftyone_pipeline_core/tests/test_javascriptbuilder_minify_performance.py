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
Measures what minifying the JavaScript adds to each request, as
javascript-builder.md asks. Each figure is the fastest of several rounds,
so a runner that pauses during one round does not fail the test. The
figures are given as a warning, so every build shows them.
"""

import time
import unittest
import warnings

from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# The requests in each round, with minifying on and with it off.
REQUESTS = 50

# The rounds timed. The fastest round of each is compared.
ROUNDS = 3

# The most minifying may add to one request, in milliseconds. About three
# times the most any runner measured, which was with coverage on.
ADDED_LIMIT_MS = 100


class ScriptEngine(FlowElement):
    """Gives a JavaScript Property, so the JavaScript Builder has a script
    to write."""

    def __init__(self):
        super(ScriptEngine, self).__init__()
        self.datakey = "script"
        self.properties = {"javascript": {"type": "javascript"}}

    def process_internal(self, flowdata):
        flowdata.set_element_data(ElementDataDictionary(
            self, {"javascript": "console.log('hello world')"}))


def pipeline(minify):
    """A Pipeline whose JavaScript Builder minifies or not."""
    return PipelineBuilder(
        {"javascript_builder_settings": {"minify": minify}}) \
        .add(ScriptEngine()).build()


def javascript_ms(pipeline, requests):
    """The milliseconds one request takes, the JavaScript included, over
    the requests, and the JavaScript the last one gave."""
    started = time.perf_counter()
    for _ in range(requests):
        with pipeline.create_flowdata() as flowdata:
            flowdata.process()
            javascript = flowdata.javascriptbuilder.javascript
    return (time.perf_counter() - started) * 1000 / requests, javascript


def fastest_ms(pipeline):
    """The fastest round's milliseconds for each request, and the
    JavaScript given."""
    rounds = [javascript_ms(pipeline, REQUESTS) for _ in range(ROUNDS)]
    return min(ms for ms, _ in rounds), rounds[-1][1]


class MinifyPerformanceTests(unittest.TestCase):

    def test_minifying_adds_little_to_each_request(self):
        minified, plain = pipeline(True), pipeline(False)
        # One request each first, so what happens once is left out.
        javascript_ms(minified, 1)
        javascript_ms(plain, 1)

        minified_ms, minified_js = fastest_ms(minified)
        plain_ms, plain_js = fastest_ms(plain)
        added_ms = minified_ms - plain_ms
        figures = (
            f"Minifying added {added_ms:.3f} ms to each request, "
            f"{minified_ms:.3f} ms minified and {plain_ms:.3f} ms not, "
            f"the fastest of {ROUNDS} rounds of {REQUESTS} requests each")
        warnings.warn(figures)

        self.assertLess(len(minified_js), len(plain_js))
        self.assertLess(added_ms, ADDED_LIMIT_MS, figures)


if __name__ == "__main__":
    unittest.main()

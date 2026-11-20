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

"""Runs the offline 51Did example, examples/fodid_example.py, which signs a
sample 51Did, reads it back and signs it again. It needs no network."""

import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "fodid_example.py"


def load_example():
    """Loads the example's file as a module, which defines its functions
    without running them, and returns the module."""
    spec = importlib.util.spec_from_file_location("fodid_example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def field(output, name):
    """The value the example printed for a field, as name : value."""
    for line in output.splitlines():
        label, _, value = line.partition(":")
        if label.strip() == name:
            return value.strip()
    return None


class FodIdExampleTests(unittest.TestCase):

    def test_run_reads_back_the_51did_it_signed(self):
        example = load_example()
        printed = io.StringIO()
        with redirect_stdout(printed):
            # Raises if signing again changes the match key, or leaves the
            # envelope as it was.
            example.run()

        output = printed.getvalue()
        payload = example.sample_payload()
        match_key = payload[
            example.SAMPLE_MATCH_KEY_OFFSET:
            example.SAMPLE_MATCH_KEY_OFFSET + example.SAMPLE_MATCH_KEY_LENGTH]
        self.assertEqual(example.DOMAIN, field(output, "Domain"))
        self.assertEqual(match_key.hex(), field(output, "Match key"))
        self.assertEqual("True", field(output, "Verifies"))
        self.assertEqual("False", field(output, "Same envelope (base64)"))
        self.assertEqual("True", field(output, "Same match key"))


if __name__ == "__main__":
    unittest.main()

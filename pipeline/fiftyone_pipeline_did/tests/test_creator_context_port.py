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

"""The creator context example listens on port 5151 by default, and on the
port the PORT environment variable names when it is set. The check reads
the example's source, so it starts no server and needs no resource key."""

import ast
import unittest
from pathlib import Path

SERVER_PY = Path(__file__).resolve().parents[1] / "examples" \
    / "creator_context_web" / "server.py"


def port_assignment():
    """The expression server.py assigns to PORT."""
    tree = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(getattr(target, "id", None) == "PORT"
                        for target in node.targets)):
            return node.value
    return None


class CreatorContextPortTests(unittest.TestCase):

    def test_listens_on_5151_unless_port_names_another(self):
        port = port_assignment()
        # int(os.environ.get("PORT", "5151"))
        self.assertIsInstance(port, ast.Call)
        get = port.args[0]
        self.assertEqual("get", get.func.attr)
        self.assertEqual(
            ["PORT", "5151"], [str(arg.value) for arg in get.args])


if __name__ == "__main__":
    unittest.main()

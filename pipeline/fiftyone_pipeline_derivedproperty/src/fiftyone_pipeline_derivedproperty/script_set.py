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
Collects scripts from the three places a script can come from, being the
scripts built into this package, files, and text held by code, along with
every fault found in any of them.
"""

import fnmatch
import os
import re

from .errors import ScriptValidationError
from .validate import Fault, validate_text

## The scripts built into this package, which are the scripts folder of the
# derived-properties submodule. The package carries that folder and nothing
# else from the submodule.
BUILT_IN_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "derived-properties",
    "scripts")

_SCRIPT_FILE = re.compile(r"\.(ya?ml|json)$", re.IGNORECASE)


def _built_in_files():
    if not os.path.isdir(BUILT_IN_FOLDER):
        return None
    return sorted(f for f in os.listdir(BUILT_IN_FOLDER)
                  if _SCRIPT_FILE.search(f))


def _name_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def builtin_script_names():
    """!
    The names of the scripts built into this package.

    @return: the names, such as HumanConfidence and IsGdpr.
    """
    files = _built_in_files()
    return [] if files is None else [_name_of(f) for f in files]


class ScriptSet(object):
    """! The scripts read so far, and every fault found in them. """

    def __init__(self):
        self.scripts = []
        self.faults = []

    def add_built_in(self, name):
        """!
        Adds a script built into this package, by its name in any case.
        """
        def fault(message):
            self.faults.append(Fault(
                name if isinstance(name, str) else None, "built in", "",
                None, message))

        if not isinstance(name, str) or name.strip() == "":
            fault("a built in script name is empty")
            return
        files = _built_in_files()
        if files is None:
            fault("the built in scripts are not in this copy of the "
                  "package, because the folder '" + BUILT_IN_FOLDER +
                  "' does not exist. In a clone of the repository, git "
                  "submodule update --init fetches them")
            return
        lower = name.strip().lower()
        found = [f for f in files if _name_of(f).lower() == lower]
        if not found:
            names = [_name_of(f) for f in files]
            fault("there is no script called '" + name.strip() + "' in "
                  "this package. The scripts in this package are " +
                  (", ".join(names) if names else "(none)") +
                  ". A script from your own environment is added with "
                  "script_files rather than scripts")
            return
        script_name = _name_of(found[0])
        with open(os.path.join(BUILT_IN_FOLDER, found[0]),
                  encoding="utf-8") as file:
            text = file.read()
        self.add_text(script_name, text, "built in " + script_name)

    def add_files(self, path):
        """!
        Adds a script file, or every file a wildcard in the file name
        matches, in order of their names. A relative path is read from the
        current folder.
        """
        if not isinstance(path, str) or path.strip() == "":
            self.faults.append(Fault(
                None, "file", "", None, "a script file path is empty"))
            return
        trimmed = path.strip()
        if "*" not in trimmed and "?" not in trimmed:
            self.add_file(trimmed)
            return
        folder = os.path.dirname(trimmed) or "."
        pattern = os.path.basename(trimmed)
        if not os.path.isdir(folder):
            self.faults.append(Fault(
                None, trimmed, "", None,
                "the folder '" + folder + "' does not exist"))
            return
        # Ordered so that a wildcard gives the same element on every
        # machine, whatever order the file system lists in.
        for file in sorted(os.listdir(folder)):
            full = os.path.join(folder, file)
            if fnmatch.fnmatch(file, pattern) and os.path.isfile(full):
                self.add_file(full)

    def add_file(self, path):
        """!
        Adds one script file. The script's Name must equal the file name
        without its extension.
        """
        try:
            with open(path, encoding="utf-8-sig") as file:
                text = file.read()
        except OSError as error:
            self.faults.append(Fault(
                _name_of(path), path, "", None,
                "the file could not be read. " + str(error)))
            return
        self.add_text(_name_of(path), text, path)

    def add_text(self, name, text, source="code"):
        """!
        Adds the text of a script, as YAML or JSON.

        @param name: the name the script's Name must equal, or None for no
            such check.
        @param text: the script.
        @param source: where the script came from, for the log and the
            fault messages.
        """
        model, faults = validate_text(text, name, source)
        if model is None:
            self.faults.extend(faults)
            return
        self.scripts.append(model)

    def compile(self):
        """!
        The scripts, once every one has validated.

        @raise ScriptValidationError: where any script did not validate.
        """
        if self.faults:
            raise ScriptValidationError(self.faults)
        return self.scripts

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

from .derived_property_element import DerivedPropertyElement
from .script_set import ScriptSet


class DerivedPropertyElementBuilder(object):
    """!
    Builds a DerivedPropertyElement from scripts built into this package,
    script files, and script text held by code, in any mix. Every fault in
    every script is reported together when the element is built.
    """

    def __init__(self):
        self._scripts = ScriptSet()

    def add_built_in_script(self, name):
        """!
        Adds a script built into this package.

        @param name: the name of the script in any case, such as
            HumanConfidence or IsGdpr.
        @return: this builder.
        """
        self._scripts.add_built_in(name)
        return self

    def add_script_file(self, path):
        """!
        Adds a script file, or every file a wildcard in the file name
        matches. The script's Name must equal the file name without its
        extension.

        @return: this builder.
        """
        self._scripts.add_files(path)
        return self

    def add_script(self, name, text):
        """!
        Adds a script held as text by your own code, as YAML or JSON.

        @param name: the name to know the script by, which the script's own
            Name must equal.
        @param text: the script.
        @return: this builder.
        """
        if not isinstance(name, str) or name.strip() == "":
            raise TypeError("A script added from code needs its name.")
        if not isinstance(text, str):
            raise TypeError("The script '" + name + "' added from code "
                            "needs its text.")
        self._scripts.add_text(name, text)
        return self

    def build(self):
        """!
        Builds the element.

        @raise ScriptValidationError: where any script does not validate.
        """
        return DerivedPropertyElement(compiled=self._scripts.compile())

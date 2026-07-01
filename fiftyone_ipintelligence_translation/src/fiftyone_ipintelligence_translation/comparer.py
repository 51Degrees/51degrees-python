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

import unicodedata


def make_comparer(culture=None):

    """!
    Return a sort key function for ordering country names.

    Python has no stable, dependency-free, process-local culture aware string
    comparer equivalent to .NET's CultureInfo / StringComparer, so a Unicode
    normalized, case-insensitive key is used instead: names are accent folded
    (NFKD, dropping combining marks) and case folded. This gives a deterministic
    alphabetical ordering that is stable across platforms. The same key function
    is used by the engine and its tests so the ordering is self-consistent.

    The culture argument is accepted for parity with the resolved locale (it is
    also surfaced as the SortingCultureUsed property) but does not change the
    ordering.
    """

    def key(name):
        if name is None:
            return ""
        decomposed = unicodedata.normalize("NFKD", str(name))
        without_marks = "".join(
            char for char in decomposed if not unicodedata.combining(char))
        return without_marks.casefold()

    return key

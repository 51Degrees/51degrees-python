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

"""The addresses the live tests of the cloud examples look up, and the
values the cloud service gives for them. The .NET tests of the same
examples look up the same addresses and require the same values, so a
test passes only when the example shows real results.
"""

# A public IPv4 address in the United Kingdom.
ADDRESS = "82.12.34.23"

# The network the address is registered to.
REGISTERED_NAME = "VMCBBUK"

# The country of the address, as a name or a code. Either will do.
COUNTRY = ("United Kingdom", "GB")

# The first and last addresses of the range that holds the address. Either
# will do.
RANGE = ("82.12.34.0", "82.12.34.255")

# An address the cloud service gives translated country names for.
COUNTRIES_ADDRESS = "185.28.167.78"


def results_for(printed, address):
    """The results an example printed for the address, which is the text
    it printed straight after the input values that hold the address, or
    None when it printed none.

    printed is the list of the texts the example gave its output function.
    """
    for index, text in enumerate(printed[:-1]):
        if f": {address}\n" in text and "Input values:" in text:
            return printed[index + 1]
    return None

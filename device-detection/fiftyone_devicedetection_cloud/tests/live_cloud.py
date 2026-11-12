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

"""Where the tests that call the live 51Degrees cloud service find their
resource key, and what they fail with when there is none or when the
answer lacks what they asked for.

The same file is in each test folder whose tests call the live cloud
service. There is no fallback to a skip, because a cloud test that passes
without calling the cloud has proved nothing.
"""

import os

# Tried in this order. _51DEGREES_RESOURCE_KEY is first because the Cloud
# 51Did workflow sets it to each key in turn, and each product's
# integration test script sets it too.
RESOURCE_KEY_NAMES = (
    "_51DEGREES_RESOURCE_KEY",
    "_51DEGREES_RESOURCE_KEY_BESPOKE",
)

ACCESSIBLE_PROPERTIES_URL = (
    "https://cloud.51degrees.com/api/v4/accessibleproperties?resource=<key>")

CREATE_KEY_URL = "https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=live_cloud.py&utm_term=resource-key-required"


def find_resource_key(names=RESOURCE_KEY_NAMES):
    """The first resource key set under any of the names, or None."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def no_resource_key(product, asks_for, several=False,
                    names=RESOURCE_KEY_NAMES):
    """What to fail with when no resource key is set.

    product names the product the key has to carry, with its article, as in
    "the device product". asks_for says what the test asks the service for.
    several is true where the message stands for a group of tests.
    """
    if several:
        opening = ("These tests call the live 51Degrees cloud service, so "
                   "they need a resource key")
        asker = "the tests ask"
    else:
        opening = ("This test calls the live 51Degrees cloud service, so "
                   "it needs a resource key")
        asker = "the test asks"
    return (
        f"{opening} and there is nothing to fall back on. None of "
        f"{', '.join(names)} is set, tried in that order. The key has to "
        f"carry {product}, because {asker} the service for {asks_for}. To "
        f"see the products a key carries, open {ACCESSIBLE_PROPERTIES_URL}. "
        f"Create a key at {CREATE_KEY_URL}.")


def answered_without(thing, reason, product):
    """What to fail with when the cloud answered without the thing asked
    for. reason is the cloud's null reason, or None when it gave none."""
    return (
        f"The cloud answered without {thing} "
        f"({reason or 'no reason given'}), which is what a key that does "
        f"not carry {product} gets.")

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

import unittest

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue

NO_VALUE = "This instance does not have a set value"


class AspectPropertyValueTests(unittest.TestCase):

    """!
    Reading the value of an AspectPropertyValue that has no value raises,
    with the reason given or, when none was given, a message saying there
    is no value, as the Null values section of properties.md in the
    specifications asks. A value that is set, whatever it is, is read back
    as it was set.
    """

    def test_reading_no_value_raises_with_a_message(self):
        cases = [
            ("no reason", AspectPropertyValue(), NO_VALUE),
            ("a None reason", AspectPropertyValue(None), NO_VALUE),
            ("an empty reason", AspectPropertyValue(""), NO_VALUE),
            ("a reason", AspectPropertyValue("No match"), "No match"),
        ]
        for name, apv, message in cases:
            with self.subTest(name):
                self.assertFalse(apv.has_value())
                with self.assertRaises(Exception) as raised:
                    apv.value()
                self.assertEqual(message, str(raised.exception))

    def test_no_reason_leaves_the_message_unset(self):
        self.assertIsNone(AspectPropertyValue().no_value_message())

    def test_a_value_is_read_as_set(self):
        for value in ["Value", None, False, 0, "", ["a", "b"]]:
            with self.subTest(value=value):
                apv = AspectPropertyValue(value=value)
                self.assertTrue(apv.has_value())
                self.assertEqual(value, apv.value())

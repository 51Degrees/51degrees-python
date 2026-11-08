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

import warnings
from enum import Enum


class MissingTranslationBehavior(Enum):

    """!
    Defines what a Translator does when there is no translation available
    for a value.
    """

    # Return the input value unchanged.
    ORIGINAL = "original"

    # Return an empty string.
    EMPTY_STRING = "empty_string"

    # Add a not-found error to the flow data and return None.
    FLOW_ERROR = "flow_error"

    @classmethod
    def from_value(cls, value):

        """!
        The member a value names. A member is returned as it is. Text names
        a member by the specification's name (Original, EmptyString or
        FlowError) or by the member's own name or value, ignoring case and
        underscores, because a configuration file cannot give a member.

        @param value: A member, or text naming one.

        @rtype: MissingTranslationBehavior
        @return: The member named.

        @raises ValueError: When the value names no member.
        """

        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            key = value.replace("_", "").lower()
            for member in cls:
                if member.name.replace("_", "").lower() == key:
                    return member
        raise ValueError(
            f"{value!r} is not a missing translation behavior. Use "
            f"Original, EmptyString or FlowError.")


# Stands for an argument the caller did not give, so that None given on
# purpose is refused like any other value that names no member.
_NOT_GIVEN = object()


def _resolve(missing_translation_behavior, behavior):

    """!
    The member the constructor arguments name. behavior is the deprecated
    name for missing_translation_behavior, so using it warns, and when both
    are given missing_translation_behavior wins. Neither given means
    ORIGINAL.
    """

    if behavior is not _NOT_GIVEN:
        # Two levels up is the caller of the constructor that called this.
        warnings.warn(
            "The 'behavior' argument is deprecated. Use "
            "'missing_translation_behavior', the name the specification "
            "gives the option.",
            DeprecationWarning,
            stacklevel=3)
        if missing_translation_behavior is _NOT_GIVEN:
            missing_translation_behavior = behavior
    if missing_translation_behavior is _NOT_GIVEN:
        return MissingTranslationBehavior.ORIGINAL
    return MissingTranslationBehavior.from_value(missing_translation_behavior)

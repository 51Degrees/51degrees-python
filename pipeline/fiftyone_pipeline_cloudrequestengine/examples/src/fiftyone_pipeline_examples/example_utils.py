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
Helpers shared by the examples, for reading their settings from the
environment and for turning property values into text.
"""

import os
import sys


class ExampleUtils:

    # The environment variable the examples read the resource key from.
    # Every 51Degrees resource key variable starts with
    # "_51DEGREES_RESOURCE_KEY".
    RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"

    # Deprecated. Use RESOURCE_KEY_ENV_VAR. The name the resource key
    # variable had before, read when RESOURCE_KEY_ENV_VAR is not set.
    LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"

    # The environment variable the examples read a licence key from, to use
    # in place of a resource key.
    LICENSE_KEY_ENV_VAR = "_51DEGREES_LICENSE_KEY"

    # Deprecated. Use LICENSE_KEY_ENV_VAR. The name the licence key
    # variable had before, read when LICENSE_KEY_ENV_VAR is not set.
    LEGACY_LICENSE_KEY_ENV_VAR = "license_key"

    # The environment variable naming a cloud service other than the public
    # one, for example one hosted privately. The value includes the api/v4
    # path, as in https://cloud.51degrees.com/api/v4/.
    CLOUD_ENDPOINT_ENV_VAR = "_51DEGREES_CLOUD_ENDPOINT"

    # Deprecated. Use CLOUD_ENDPOINT_ENV_VAR. The name that variable had
    # before, read when CLOUD_ENDPOINT_ENV_VAR is not set.
    ENDPOINT_ENV_VAR = "cloud_endpoint"

    # The environment variable holding the origin to send with each request
    # to the cloud service, for a resource key limited to particular
    # domains, which only answers a request whose origin is one of them.
    CLOUD_REQUEST_ORIGIN_ENV_VAR = "_51DEGREES_CLOUD_REQUEST_ORIGIN"

    # Deprecated. Use CLOUD_REQUEST_ORIGIN_ENV_VAR. The name that variable
    # had before, read when CLOUD_REQUEST_ORIGIN_ENV_VAR is not set.
    ORIGIN_ENV_VAR = "cloud_request_origin"

    # The text shown for a value the results do not hold.
    UNKNOWN = "Unknown"

    @staticmethod
    def get_resource_key():
        return ExampleUtils.__get_env_variable(
            ExampleUtils.RESOURCE_KEY_ENV_VAR,
            ExampleUtils.LEGACY_RESOURCE_KEY_ENV_VAR)

    @staticmethod
    def get_license_key():
        return ExampleUtils.__get_env_variable(
            ExampleUtils.LICENSE_KEY_ENV_VAR,
            ExampleUtils.LEGACY_LICENSE_KEY_ENV_VAR)

    @staticmethod
    def get_cloud_endpoint():
        return ExampleUtils.__get_env_variable(
            ExampleUtils.CLOUD_ENDPOINT_ENV_VAR,
            ExampleUtils.ENDPOINT_ENV_VAR)

    @staticmethod
    def get_cloud_request_origin():
        return ExampleUtils.__get_env_variable(
            ExampleUtils.CLOUD_REQUEST_ORIGIN_ENV_VAR,
            ExampleUtils.ORIGIN_ENV_VAR)

    # The old names already reported as deprecated, so each is reported
    # once.
    __reported_old_names = set()

    @staticmethod
    def __get_env_variable(name, old_name):
        """!
        The value of the environment variable name, or an empty string.
        When name is unset or empty the name the variable had before is
        read, and using it prints once that the old name is deprecated.
        """

        value = os.environ.get(name)
        if value:
            return value
        value = os.environ.get(old_name)
        if not value:
            return ""
        if old_name not in ExampleUtils.__reported_old_names:
            ExampleUtils.__reported_old_names.add(old_name)
            print(
                f"The {old_name} environment variable is deprecated and {name} "
                f"replaces it. The value was read from {old_name} because {name} "
                f"is not set, so set {name} to the same value.",
                file=sys.stderr)
        return value

    @staticmethod
    def name_values(section, property_names):
        """!
        The names a request to the cloud service uses for properties of one
        section of its answer, each as "section.property".
        """

        return [f"{section}.{name}" for name in property_names]

    @staticmethod
    def get_element(flowdata, datakey):
        """!
        The results of one engine, or None when the flow data holds none,
        for example because the cloud request failed.
        """

        try:
            return flowdata.get(datakey)
        except Exception:
            return None

    @staticmethod
    def get_value(element_data, property_name):
        """!
        The value of a property, or None when the results do not include
        the property at all. Reading a property the key in use does not
        carry raises, so a page or report that lists a fixed set of
        properties reads each one through here.
        """

        if element_data is None:
            return None
        try:
            return element_data.get(property_name)
        except Exception:
            return None

    @staticmethod
    def format_value(value, decimals=None):
        """!
        A property value as text. A list is joined with commas, an entry of
        a weighted value is followed by its weighting as a percentage, and
        decimals sets the number of places a number is shown to.

        The cloud service gives some values inside an object with a "value"
        key, for example the WKT text of an area, so the object's value is
        shown rather than the object.
        """

        if isinstance(value, list):
            return ", ".join(ExampleUtils.format_value(item) for item in value)
        if isinstance(value, dict) and "value" in value:
            if "weighting" in value:
                return (f"{value['value']} "
                        f"({ExampleUtils.as_percentage(value['weighting'])}%)")
            return str(value["value"])
        if decimals is not None and isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        return str(value)

    @staticmethod
    def as_percentage(weighting):
        return f"{round(weighting * 100, 2):g}"

    @staticmethod
    def get_human_readable(element_data, property_name, decimals=None):
        """!
        A property value for display.

        A property can be unavailable for three reasons, and each one reads
        differently so the person running the example can tell them apart.
        The property may have a value, it may have no value with the cloud
        service giving a reason (most often that the key in use is not
        entitled to it), or it may not be in the results at all.
        """

        value = ExampleUtils.get_value(element_data, property_name)

        if value is None:
            return (f"{ExampleUtils.UNKNOWN} (the property '{property_name}' "
                    "is not in the results, so the key in use does not "
                    "include it)")

        if value.has_value():
            return ExampleUtils.format_value(value.value(), decimals)

        reason = value.no_value_message()
        if not reason:
            return (f"{ExampleUtils.UNKNOWN} (the cloud service returned no "
                    f"value for '{property_name}' and gave no reason)")

        return f"{ExampleUtils.UNKNOWN} ({reason})"

    @staticmethod
    def get_value_or_unknown(element_data, property_name, decimals=None):
        """!
        A property value as text, or "Unknown" when there is none, for use
        where the reason would get in the way, such as a table cell or a
        sentence. decimals sets the number of places a number is shown to.
        """

        value = ExampleUtils.get_value(element_data, property_name)
        if value is None or not value.has_value():
            return ExampleUtils.UNKNOWN
        return ExampleUtils.format_value(value.value(), decimals)

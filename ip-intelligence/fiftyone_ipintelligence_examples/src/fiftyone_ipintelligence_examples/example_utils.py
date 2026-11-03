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

from datetime import datetime, timedelta
import os
from pathlib import Path


class ExampleUtils:
    # Timeout used when searching for files.
    FIND_FILES_TIMEOUT_S = 5

    # If data file is older than this number of days then a warning will
    # be displayed.
    DATA_FILE_AGE_WARNING = 30

    # The default environment variable used to get the resource key
    # to use when running examples.
    RESOURCE_KEY_ENV_VAR = "resource_key"

    ENDPOINT_ENV_VAR = "cloud_endpoint"

    # The default environment variable used to get the data file path
    # to use when running examples.
    DATA_FILE_ENV_VAR = "IPINTELLIGENCEDATAFILE"

    @staticmethod
    def get_human_readable(ip_data, property):
        try:
            value = ip_data.get(property)
        except Exception:
            return "Property not found in data file"
        if value and value.has_value():
            return ExampleUtils.format_value(value.value())
        else:
            return f"Unknown ({value.no_value_message()})"

    @staticmethod
    def format_value(value):

        """!
        Render a property value as a human readable string. Weighted value
        properties (for example countrycodesgeographical) are returned as a
        list of {value, weighting} dictionaries; these are formatted as the
        value on its own when the weighting is 1, or "value @ weighting"
        otherwise, matching the .NET examples.
        """

        if (isinstance(value, list) and len(value) > 0 and
                isinstance(value[0], dict) and "value" in value[0]):
            parts = []
            for item in value:
                # On-premise results carry a normalised "weighting" (0-1);
                # cloud results carry a raw "rawweighting" (0-65535).
                weighting = item.get("weighting")
                if weighting is None and "rawweighting" in item:
                    weighting = item["rawweighting"] / 65535.0
                item_value = item.get("value")
                if weighting is None or abs(weighting - 1.0) < 0.0001:
                    parts.append(f"'{item_value}'")
                else:
                    parts.append(f"('{item_value}' @ {weighting:.4f})")
            return ", ".join(parts)
        return str(value)

    @staticmethod
    def get_value(ip_data, property):

        """!
        Return the value wrapper for a property, or None if the property is
        not present in the data file. Accessing a property directly raises
        when it is absent; this allows an example to request a fixed list of
        properties against any data file tier (for example the network-only
        ASN data file) without failing.
        """

        try:
            return ip_data.get(property)
        except Exception:
            return None

    @staticmethod
    def get_resource_key():
        return ExampleUtils.__get_env_variable(ExampleUtils.RESOURCE_KEY_ENV_VAR)

    @staticmethod
    def get_cloud_endpoint():
        return ExampleUtils.__get_env_variable(ExampleUtils.ENDPOINT_ENV_VAR)

    @staticmethod
    def find_file(file_name):

        """!
        Find the specified file. First checks the data file environment
        variable, then searches up the directory tree from the current
        working directory looking in 'assets' and 'ip-intelligence-data'
        folders.
        """

        env = os.environ.get(ExampleUtils.DATA_FILE_ENV_VAR)
        if env and os.path.basename(env) == file_name and os.path.isfile(env):
            return env

        current = Path(os.getcwd()).resolve()
        roots = [current, *current.parents]
        for root in roots[:8]:
            for sub_dir in [
                    ".",
                    "assets",
                    "ip-intelligence-data",
                    os.path.join("cxx", "ip-intelligence-data")]:
                candidate = os.path.join(str(root), sub_dir, file_name)
                if os.path.isfile(candidate):
                    return candidate

        return None

    @staticmethod
    def get_data_file_date(pipeline):
        engine = pipeline.flow_elements_list["ip"]
        return engine.data_file.get_date_published() if engine.data_file else None

    @staticmethod
    def check_data_file(pipeline, logger):

        """!
        Display information about the data file and log warnings if it
        is old or a Lite file.
        """

        engine = pipeline.flow_elements_list["ip"]

        if hasattr(engine, "engine"):
            product = engine.engine.getProduct()
            published = engine.engine.getPublishedTime()
            date_published = datetime(
                published.getYear(),
                published.getMonth(),
                published.getDay())
            age = datetime.now() - date_published

            logger.log("info",
                f"Using a '{product}' data file created "
                f"'{date_published.date()}'")

            if age > timedelta(days=ExampleUtils.DATA_FILE_AGE_WARNING):
                logger.log("warning",
                    f"This data file is more than "
                    f"{ExampleUtils.DATA_FILE_AGE_WARNING} days old. A more "
                    f"recent data file may be needed to correctly resolve "
                    f"the latest IP addresses. The latest data file is "
                    f"available from the ip-intelligence-data repository on "
                    f"GitHub https://github.com/51Degrees/ip-intelligence-data.")

            if product == "Lite":
                logger.log("warning",
                    "This example is using the 'Lite' data file. This is "
                    "used for illustration, and has limited properties. A "
                    "more complete data file can be obtained from "
                    "https://51degrees.com/pricing")

    @staticmethod
    def __get_env_variable(name):
        value = os.environ.get(name)
        if not value:
            value = os.environ.get(name.upper())
        return value

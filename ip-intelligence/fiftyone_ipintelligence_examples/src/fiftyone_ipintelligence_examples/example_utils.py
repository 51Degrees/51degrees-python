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
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


class ExampleUtils:
    # Timeout used when searching for files.
    FIND_FILES_TIMEOUT_S = 5

    # If data file is older than this number of days then a warning will
    # be displayed.
    DATA_FILE_AGE_WARNING = 30

    # The default environment variable used to get the resource key
    # to use when running examples.
    CLOUD_RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"

    # Deprecated. Use CLOUD_RESOURCE_KEY_ENV_VAR. The name the resource key
    # variable had before, read when CLOUD_RESOURCE_KEY_ENV_VAR is not set.
    RESOURCE_KEY_ENV_VAR = "resource_key"

    # The environment variable the data file update example reads a licence
    # key from.
    LICENSE_KEY_ENV_VAR = "_51DEGREES_LICENSE_KEY"

    # Deprecated. Use LICENSE_KEY_ENV_VAR. The name the licence key
    # variable had before, read when LICENSE_KEY_ENV_VAR is not set.
    LEGACY_LICENSE_KEY_ENV_VAR = "license_key"

    # The environment variable naming a cloud service other than the public
    # one.
    CLOUD_ENDPOINT_ENV_VAR = "_51DEGREES_CLOUD_ENDPOINT"

    # Deprecated. Use CLOUD_ENDPOINT_ENV_VAR. The name that variable had
    # before, read when CLOUD_ENDPOINT_ENV_VAR is not set.
    ENDPOINT_ENV_VAR = "cloud_endpoint"

    # The default environment variable used to get the data file path
    # to use when running examples.
    IPI_PATH_ENV_VAR = "_51DEGREES_IPI_PATH"

    # Deprecated. Use IPI_PATH_ENV_VAR. The name that variable had before,
    # read when IPI_PATH_ENV_VAR is not set.
    DATA_FILE_ENV_VAR = "IPINTELLIGENCEDATAFILE"

    # The data repository's IP intelligence folder, from the root of a
    # checkout of this repository. Each file the data repository links to
    # belongs in this folder, beside its .link file.
    DATA_FOLDER = os.path.join("cxx", "data", "ip-intelligence")

    # The data repository's device detection folder, for the examples that
    # use both products.
    DEVICE_DETECTION_DATA_FOLDER = os.path.join("cxx", "data", "device-detection")

    # Sent with each download, so the downloads these examples make can be
    # counted. It is left out inside GitHub Actions, where the data
    # repository's script names the build instead, so that test runs are
    # not counted as people using the examples.
    DOWNLOAD_SOURCE = "examples-51degrees-python"

    # Shown in place of a value for a property that the data file in use
    # does not have. Every property the examples ask for is in the
    # Enterprise data file.
    NEEDS_ENTERPRISE = "needs the Enterprise data file"

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
        """!
        The resource key from the environment, or None. The old name is
        also read in upper case, as it was before.
        """

        return (
            ExampleUtils.__get_env_variable(
                ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR,
                ExampleUtils.RESOURCE_KEY_ENV_VAR)
            or ExampleUtils.__get_env_variable(
                ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR,
                ExampleUtils.RESOURCE_KEY_ENV_VAR.upper()))

    @staticmethod
    def get_license_key():
        return ExampleUtils.__get_env_variable(
            ExampleUtils.LICENSE_KEY_ENV_VAR,
            ExampleUtils.LEGACY_LICENSE_KEY_ENV_VAR)

    @staticmethod
    def get_cloud_endpoint():
        """!
        The cloud endpoint from the environment, or None. The old name is
        also read in upper case, as it was before.
        """

        return (
            ExampleUtils.__get_env_variable(
                ExampleUtils.CLOUD_ENDPOINT_ENV_VAR,
                ExampleUtils.ENDPOINT_ENV_VAR)
            or ExampleUtils.__get_env_variable(
                ExampleUtils.CLOUD_ENDPOINT_ENV_VAR,
                ExampleUtils.ENDPOINT_ENV_VAR.upper()))

    @staticmethod
    def find_file(file_name):

        """!
        Find the specified file. First checks the data file environment
        variable, then searches up the directory tree from the current
        working directory looking in 'assets' and the data repository's
        folders. A file the data repository links to is downloaded there
        when it is missing.
        """

        env = ExampleUtils.__get_env_variable(
            ExampleUtils.IPI_PATH_ENV_VAR, ExampleUtils.DATA_FILE_ENV_VAR)
        if env and os.path.basename(env) == file_name and os.path.isfile(env):
            return env

        current = Path(os.getcwd()).resolve()
        roots = [current, *current.parents]
        folders = [
            ExampleUtils.DATA_FOLDER,
            ExampleUtils.DEVICE_DETECTION_DATA_FOLDER]
        for root in roots[:8]:
            for sub_dir in [".", "assets", *folders]:
                candidate = os.path.join(str(root), sub_dir, file_name)
                if os.path.isfile(candidate):
                    return candidate

        for root in roots[:8]:
            for folder in folders:
                candidate = os.path.join(str(root), folder, file_name)
                if os.path.isfile(candidate + ".link"):
                    return ExampleUtils.__download(candidate)

        return None

    @staticmethod
    def __download(path):

        """!
        Download a file the data repository links to, by running the data
        repository's own script for that file, and return its path, or None
        when it could not be downloaded. The data repository is the folder
        above the one that holds the file's .link.
        """

        name = os.path.basename(path)
        data = os.path.dirname(os.path.dirname(path))
        in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        environment = None
        if os.name == "nt":
            # PowerShell 7 when it is on the path, otherwise Windows
            # PowerShell, which, started from PowerShell 7, inherits its
            # module path and then cannot load its own commands.
            power_shell = "pwsh" if shutil.which("pwsh") else "powershell"
            command = [
                power_shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", os.path.join(data, "get-data-files.ps1"), name]
            if not in_actions:
                command += ["-Source", ExampleUtils.DOWNLOAD_SOURCE]
            if power_shell == "powershell":
                environment = dict(os.environ)
                environment.pop("PSModulePath", None)
            text = subprocess.list2cmdline(command)
        else:
            command = ["sh", os.path.join(data, "get-data-files.sh")]
            if not in_actions:
                command += ["-s", ExampleUtils.DOWNLOAD_SOURCE]
            command.append(name)
            text = shlex.join(command)

        # Flushed first, because the script writes to the same output.
        print(f"{name} is missing, so it is being downloaded by running\n"
              f"{text}", flush=True)
        try:
            subprocess.run(command, check=False, env=environment)
        except OSError:
            pass
        if os.path.isfile(path):
            return path
        print(f"{name} could not be downloaded. Run this command to try "
              f"again.\n{text}")
        return None

    @staticmethod
    def has_property(engine, name):

        """!
        True when the engine's data file has the property. The free Lite data
        file has the registration properties, such as RegisteredName, and the
        free ASN data file the ASN properties, such as AsnName. The data
        file's own list is read, because the engine's properties are only
        those it was built to give.
        """

        properties = engine.engine.getMetaData().getProperties()
        name = name.lower()
        for index in range(properties.getSize()):
            if properties.getByIndex(index).getName().lower() == name:
                return True
        return False

    @staticmethod
    def is_free_data_file(engine):

        """!
        True when the engine uses one of the free data files, Lite or ASN.
        Only the Enterprise data file has the range properties, so a check
        for IpRangeStart tells them apart.
        """

        return not ExampleUtils.has_property(engine, "IpRangeStart")

    @staticmethod
    def is_free_data_file_at(data_file):

        """!
        True when the data file at the path is one of the free data files.
        The data file is opened with the low memory profile, which reads
        little of it.
        """

        with ExampleUtils.__open(data_file) as pipeline:
            return ExampleUtils.is_free_data_file(
                pipeline.flow_elements_list["ip"])

    @staticmethod
    def get_enterprise_value(engine, ip_data, property):

        """!
        Format a property for display, or say that it needs the Enterprise
        data file when the engine's data file does not have it. The value
        is only read when the data file has the property.
        """

        if not ExampleUtils.has_property(engine, property):
            return ExampleUtils.NEEDS_ENTERPRISE
        return ExampleUtils.get_human_readable(ip_data, property)

    @staticmethod
    def lacks_enterprise_properties(data_file, purpose, properties, output,
                                    contact_us):

        """!
        For an example that needs properties only the Enterprise data file
        has, report when the data file has none of them, and then say so and
        where to ask for a copy of the Enterprise data file. The data file is
        opened with the low memory profile, which reads little of it.
        @param purpose: What the example does, as the start of a sentence,
        for example "Comparing known locations with IP Intelligence".
        @param contact_us: The link to the contact page, tagged with the
        example's file, so that an enquiry can be traced to the example.
        """

        with ExampleUtils.__open(data_file) as pipeline:
            engine = pipeline.flow_elements_list["ip"]
            if any(ExampleUtils.has_property(engine, name)
                   for name in properties):
                return False
        if len(properties) == 1:
            names = properties[0]
        else:
            names = ", ".join(properties[:-1]) + " and " + properties[-1]
        output(f"{purpose} needs the {names} properties, which only the "
               "Enterprise data file has. The data file in use has none of "
               "them, so the example stops here. Contact us for a copy of "
               f"the Enterprise data file at {contact_us}")
        return True

    @staticmethod
    def get_enterprise_note(contact_us):

        """!
        Where to ask for a copy of the Enterprise data file, written after an
        example has shown properties that the data file in use does not
        have. The link is tagged with the example's file, so that an enquiry
        can be traced to the example.
        """

        return ("Some of these properties need the Enterprise data file. "
                f"Contact us for a copy at {contact_us}")

    @staticmethod
    def get_enterprise_offer(contact_us):

        """!
        What the Enterprise data file adds and where to ask for a copy,
        written after an example that shows no location properties has run
        on a free data file.
        """

        return ("This example used a free data file. The Enterprise data "
                "file adds the location, range and connection properties. "
                f"Contact us for a copy at {contact_us}")

    @staticmethod
    def __open(data_file):

        """!
        A pipeline that reads the data file with the low memory profile.
        """

        from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
        return IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = "LowMemory",
            usage_sharing = False,
            auto_update = False,
            licence_keys = "").build()

    @staticmethod
    def get_data_file_date(pipeline):
        engine = pipeline.flow_elements_list["ip"]
        return engine.data_file.get_date_published() if engine.data_file else None

    @staticmethod
    def check_data_file(pipeline, logger):

        """!
        Display information about the data file and log a warning if it is
        old. An example run on a free data file says what the Enterprise
        data file adds in its own output.
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
                    f"the latest IP addresses. Get the latest free data files "
                    f"by running cxx/data/get-data-files.sh -u ip-intelligence, "
                    f"or cxx/data/get-data-files.ps1 ip-intelligence -Update "
                    f"on Windows.")

    # The old names already reported as deprecated, so each is reported
    # once.
    __reported_old_names = set()

    @staticmethod
    def __get_env_variable(name, old_name):
        """!
        The value of the environment variable name, or None. When name is
        unset or empty the name the variable had before is read, and using
        it prints once that the old name is deprecated.
        """

        value = os.environ.get(name)
        if value:
            return value
        value = os.environ.get(old_name)
        if not value:
            return None
        if old_name not in ExampleUtils.__reported_old_names:
            ExampleUtils.__reported_old_names.add(old_name)
            print(
                f"The {old_name} environment variable is deprecated and {name} "
                f"replaces it. The value was read from {old_name} because {name} "
                f"is not set, so set {name} to the same value.",
                file=sys.stderr)
        return value

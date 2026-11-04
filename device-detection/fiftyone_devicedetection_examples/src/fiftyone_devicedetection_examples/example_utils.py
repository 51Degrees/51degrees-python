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
from threading import Event, Thread
import os
import shlex
import subprocess
from pathlib import Path


class ExampleUtils:
    # Timeout used when searching for files.
    FIND_FILES_TIMEOUT_S = 5

    # If data file is older than this number of days then a warning will
    # be displayed.
    DATA_FILE_AGE_WARNING = 30

    # The environment variable used to get the resource key to use when
    # running examples. This follows the 51Degrees convention that every
    # resource key variable starts with "_51DEGREES_RESOURCE_KEY".
    RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"

    # The environment variable this repository used before the convention
    # above was adopted. It is still read, so an existing setup keeps
    # working, but new setups should use RESOURCE_KEY_ENV_VAR.
    LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"

    ENDPOINT_ENV_VAR = "cloud_endpoint"

    # The environment variable an on-premise example reads the path of its
    # device detection data file from, when one is given, in place of the
    # file named in its configuration.
    DATA_FILE_ENV_VAR = "51DEGREES_DD_PATH"

    # The data repository's device detection folder, from the root of a
    # checkout of this repository. Each file the data repository links to
    # belongs in this folder, beside its .link file.
    DATA_FOLDER = os.path.join("cxx", "data", "device-detection")

    # Sent with each download, so the downloads these examples make can be
    # counted.
    DOWNLOAD_SOURCE = "examples-51degrees-python"

    @staticmethod
    def get_resource_key_from_config(config):
        key = ""
        for element in config["PipelineOptions"]["Elements"]:
            if element["elementName"] == "CloudRequestEngine":
                key = element["elementParameters"]["settings"]["resource_key"]

        return key

    @staticmethod
    def set_resource_key_in_config(config, key):
        for element in config["PipelineOptions"]["Elements"]:
            if element["elementName"] == "CloudRequestEngine":
                element["elementParameters"]["settings"]["resource_key"] = key

    @staticmethod
    def get_data_file_from_config(config):
        file = ""
        for element in config["PipelineOptions"]["Elements"]:
            if element["elementName"] == "DeviceDetectionOnPremise":
                file = element["elementParameters"]["data_file_path"]

        return file

    @staticmethod
    def set_data_file_in_config(config, file):
        for element in config["PipelineOptions"]["Elements"]:
            if element["elementName"] == "DeviceDetectionOnPremise":
                element["elementParameters"]["data_file_path"] = file

    @staticmethod
    def get_human_readable(device, property):
        """!
        Format a property value for display.

        A property can be unavailable for three reasons, and each one reads
        differently so the person running the example can tell them apart.
        The property may have a value, it may have no value with the cloud
        service giving a reason (most often that the resource key is not
        entitled to it), or it may not be in the results at all.
        """

        try:
            value = device.get(property)
        except Exception:
            value = None

        if value is None:
            return (f"Unknown (the property '{property}' is not in the "
                    "results, so the current resource key does not "
                    "include it)")

        if value.has_value():
            result = value.value()
            if isinstance(result, list):
                return ", ".join(str(item) for item in result)
            return result

        reason = value.no_value_message()

        if not reason:
            return (f"Unknown (the cloud service returned no value for "
                    f"'{property}' and gave no reason)")

        return f"Unknown ({reason})"

    @staticmethod
    def get_profiles(hardware):
        """!
        Read the list of hardware profiles from the "hardware" element data.

        An empty list is returned when the resource key has no access to the
        hardware aspect at all, because reading a property that is not there
        raises rather than returning an empty list.
        """

        try:
            profiles = hardware.profiles
        except Exception:
            return []

        return profiles if isinstance(profiles, list) else []

    @staticmethod
    def get_no_profiles_message():
        """!
        The line printed when a lookup returned no device profiles at all.
        """

        return ("\tNo device profiles were returned. The current resource "
                "key does not include the hardware properties this example "
                "needs. See "
                "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-example_utils.py&utm_term=no-profiles")

    @staticmethod
    def get_resource_key():
        key = ExampleUtils.__get_env_variable(ExampleUtils.RESOURCE_KEY_ENV_VAR)

        if not key:
            key = ExampleUtils.__get_env_variable(
                ExampleUtils.LEGACY_RESOURCE_KEY_ENV_VAR)

        return key

    @staticmethod
    def get_missing_resource_key_message():
        """!
        The message shown when no resource key is set, naming the variable
        that was wanted rather than leaving the reader to guess.
        """

        return (f"No resource key found. Set the environment variable "
                f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}' (the older name "
                f"'{ExampleUtils.LEGACY_RESOURCE_KEY_ENV_VAR}' is still "
                "read). Create a resource key for free at "
                "https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-example_utils.py&utm_term=resource-key-required")

    @staticmethod
    def get_data_file_path():
        return ExampleUtils.__get_env_variable(ExampleUtils.DATA_FILE_ENV_VAR)

    @staticmethod
    def get_cloud_endpoint():
        return ExampleUtils.__get_env_variable(ExampleUtils.ENDPOINT_ENV_VAR)

    @staticmethod
    def __get_env_variable(name):
        if name in os.environ:
            return os.environ[name]
        else:
            return ""

    # Find the specified file. A path to a file that exists is returned as
    # it is. Next, the data repository's folder is checked in the working
    # directory and in each directory above it, and a file the data
    # repository links to is downloaded there when it is missing. Otherwise
    # the working directory is searched for a file with the same name, then
    # each parent directory in turn. None is returned when nothing is found.
    @staticmethod
    def find_file(file_name):
        path = Path(file_name).absolute()
        if path.is_file():
            return str(path.resolve())

        # The data repository's copy is preferred to a file with the same
        # name elsewhere in the tree, which may be out of date or a Git LFS
        # pointer.
        current = Path(os.getcwd()).absolute()
        for root in [current, *current.parents]:
            candidate = root / ExampleUtils.DATA_FOLDER / path.name
            if candidate.is_file():
                return str(candidate)
            if candidate.with_name(candidate.name + ".link").is_file():
                return ExampleUtils.__download(str(candidate))

        stop_event = Event()
        result = [None]
        # Start the file system search as a separate task.
        search_task = Thread(target=ExampleUtils.__find_file, args=(file_name, stop_event, result))
        # Wait for either the search or a timeout task to complete.
        search_task.start()
        search_task.join(ExampleUtils.FIND_FILES_TIMEOUT_S)
        if search_task.is_alive():
            stop_event.set()

        # If search has not got a result then return null.
        return result[0]

    @staticmethod
    def __find_file(file_name, stop_event, result, search_dir=None):
        # Get the absolute path of the file to search for
        _file = Path(file_name).absolute().resolve()

        # Check if the file exists
        # If it does, set the result and return
        if _file.is_file():
            result[0] = str(_file)
            return

        # If this is the first iteration - then set
        # the search directory to the current working directory
        if search_dir is None:
            search_dir = Path(os.getcwd()).absolute()

        # Search for the file in the current directory
        files = list(search_dir.rglob(_file.name))

        # If the file is found in the current directory
        # then set the result and return
        if len(files):
            result[0] = str(files[0].absolute())
            return

        # If the file is not found in the current directory
        # then move to the parent directory and repeat the process
        # unless the stop event is set
        # or the parent directory is the same as the current directory
        # (i.e. the root directory)
        if search_dir.parent != search_dir and not stop_event.is_set():
            ExampleUtils.__find_file(file_name, stop_event, result, search_dir.parent)

    # Download a file the data repository links to, by running the data
    # repository's own script for that file, and return its path, or None
    # when it could not be downloaded. The data repository is the folder
    # above the one that holds the file's .link.
    @staticmethod
    def __download(path):
        name = os.path.basename(path)
        data = os.path.dirname(os.path.dirname(path))
        if os.name == "nt":
            command = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", os.path.join(data, "get-data-files.ps1"), name,
                "-Source", ExampleUtils.DOWNLOAD_SOURCE]
            text = subprocess.list2cmdline(command)
        else:
            command = [
                "sh", os.path.join(data, "get-data-files.sh"),
                "-s", ExampleUtils.DOWNLOAD_SOURCE, name]
            text = shlex.join(command)

        # Flushed first, because the script writes to the same output.
        print(f"{name} is missing, so it is being downloaded by running\n"
              f"{text}", flush=True)
        try:
            subprocess.run(command, check=False)
        except OSError:
            pass
        if os.path.isfile(path):
            return path
        print(f"{name} could not be downloaded. Run this command to try "
              f"again.\n{text}")
        return None

    @staticmethod
    def get_data_file_date(engine):
        date = engine.engine.getPublishedTime()
        return datetime(date.getYear(), date.getMonth(), date.getDay())

    @staticmethod
    def data_file_is_old(engine):
        data_file_date = ExampleUtils.get_data_file_date(engine)
        return datetime.now() > data_file_date + timedelta(days = ExampleUtils.DATA_FILE_AGE_WARNING)

    @staticmethod
    def get_data_file_tier(engine):
        return engine.engine.getProduct()

    @staticmethod
    def check_data_file(pipeline, logger):
        # Get the 'engine' element within the pipeline that
        # performs device detection. We can use this to get
        # details about the data file as well as meta-data
        # describing things such as the available properties.
        engine = pipeline.get_element("device")

        if engine != None:
            data_file_date = ExampleUtils.get_data_file_date(engine)

            logger.log("info",
                "Using a " +
                f"'{ExampleUtils.get_data_file_tier(engine)}' data file created " +
                f"'{data_file_date}' from location " +
                f"'{engine.data_file_path}'")

        if ExampleUtils.data_file_is_old(engine):
            logger.log("warning",
                "This example is using a data file " +
                f"that is more than '{ExampleUtils.DATA_FILE_AGE_WARNING}' days " +
                "old. A more recent data file may be needed to " +
                "correctly detect the latest devices, browsers, " +
                "etc. Get the latest lite data file by running " +
                "cxx/data/get-data-files.sh -u 51Degrees-LiteV4.1.hash, " +
                "or cxx/data/get-data-files.ps1 51Degrees-LiteV4.1.hash " +
                "-Update on Windows. " +
                "Find out about the Enterprise data file, which " +
                "includes automatic updates, on our pricing page: " +
                "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-example_utils.py&utm_term=data-file-age-warning")

        if ExampleUtils.get_data_file_tier(engine) == "Lite":
            logger.log("warning",
                "This example is using the 'Lite' " +
                "data file. This is used for illustration, and " +
                "has limited accuracy and capabilities. Find " +
                "out about the Enterprise data file on our " +
                "pricing page: https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-example_utils.py&utm_term=lite-data-file")

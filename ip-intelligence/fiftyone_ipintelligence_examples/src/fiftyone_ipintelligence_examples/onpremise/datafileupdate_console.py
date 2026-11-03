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

## @example onpremise/datafileupdate_console.py
# @brief Data File Update Console Example - On-premise
#
# This example illustrates the parameters that control when a new data file
# is sought and when it is loaded by the on-premise IP intelligence engine.
#
# Three aspects are demonstrated:
# - Update on start-up
# - Filesystem watcher
# - Daily auto-update
#
# ## License Key
# In order to run this example you will need a 51Degrees Enterprise license,
# which can be purchased from our pricing page: https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-datafileupdate_console.py&utm_term=header.
# Supply the license key as the first command line argument or in the
# 'license_key' environment variable.
#
# ## Update on start-up
# Configure the pipeline to download an Enterprise data file on start-up.
# This requires a license key, a writable file location, a temporary data
# copy (create_temp_data_copy=True), a DataFileUpdateService, and
# update_on_start=True (which blocks pipeline creation until the file is
# downloaded).
#
# ## Filesystem watcher
# Configure the pipeline to watch the loaded data file on disk and reload it
# when it changes (file_system_watcher=True). Useful if you download files
# yourself and drop them into place.
#
# ## Daily auto-update
# Each data file records when the next file is expected. With auto_update
# enabled the pipeline connects to the 51Degrees distributor after that time
# to download any newer file. polling_interval and
# update_time_maximum_randomisation tune how often and how randomly the
# check happens.
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import os
import shutil
import sys
import threading
from datetime import datetime

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import ENTERPRISE_DATAFILE_NAME
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService
from fiftyone_pipeline_engines.datafile_update_service import UpdateStatus

# Environment variable checked for the license key if one is not supplied as
# a command line argument.
UPDATE_EXAMPLE_LICENSE_KEY_NAME = "license_key"

# The product type passed to the 51Degrees distributor. This identifies the
# IP intelligence Enterprise product and may need to be adjusted to match
# the product your license entitles you to.
DATA_UPDATE_PRODUCT_TYPE = "V4Enterprise"

DEFAULT_DATA_FILENAME = os.path.join(
    os.path.expanduser("~"), ENTERPRISE_DATAFILE_NAME)


class UpdateEvent(threading.Event):
    def __init__(self):
        self.status = None
        super().__init__()

    def set(self, status):
        super().set()
        self.status = status

    def clear(self):
        self.status = None
        super().clear()


class DataFileUpdateConsole():
    def run(self, data_file, license_key, interactive, logger, output):
        logger.log("info", "Starting example")

        # Try to find a license key in the environment if not supplied.
        if not license_key:
            license_key = os.environ.get(UPDATE_EXAMPLE_LICENSE_KEY_NAME)

        if not license_key:
            logger.log("error",
                "In order to run this example you will need a 51Degrees "
                "Enterprise license, which can be obtained on a trial basis "
                "or purchased from our pricing page https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-datafileupdate_console.py&utm_term=run. "
                "You must supply the license key as an argument to this "
                "program, or in an environment variable named "
                f"'{UPDATE_EXAMPLE_LICENSE_KEY_NAME}'")
            raise Exception("No license key available")

        # Work out where the downloaded file will be put. The directory must
        # exist; the file itself need not.
        if data_file is None:
            data_file = os.path.realpath(DEFAULT_DATA_FILENAME)
            logger.log("warning",
                f"No filename specified. Using default '{data_file}' which "
                "will be downloaded to that location on start-up, if it does "
                "not exist already")
        elif not os.path.exists(os.path.dirname(os.path.abspath(data_file))):
            logger.log("error",
                "The directory must exist when specifying a location for a "
                f"new file to be downloaded. Path specified was '{data_file}'")
            raise Exception("Directory for new file must exist")

        copy_data_file_name = data_file + ".bak"

        # Confirm before using the licensed download allocation.
        if interactive:
            output("Please note - this example will use available downloads "
                   "in your licensed allocation.")
            user_input = input("Do you wish to continue with this example (y)? ")
            if not user_input or not user_input.lower().startswith("y"):
                logger.log("info", "Stopping example without download")
                return

        if os.path.exists(data_file):
            logger.log("info", f"Existing data file copied to {copy_data_file_name}")
            shutil.copy(data_file, copy_data_file_name)

        logger.log("info",
            "Creating pipeline and initiating update on start-up - please "
            "wait for that to complete")

        update_event = UpdateEvent()
        update_service = DataFileUpdateService()
        update_service.on_complete(lambda status, file: update_event.set(status))

        # Build the pipeline, configuring it for automatic updates.
        IpIntelligencePipelineBuilder(
            # The file need not exist when using update on start-up, but its
            # directory must. Any file present is overwritten, so the engine
            # is configured to use a temporary copy.
            data_file_path = data_file,
            create_temp_data_copy = True,
            # The update listener notifies us when an update is complete.
            data_file_update_service = update_service,
            # A license key is required for automatic updates.
            licence_keys = license_key,
            # Check for an update before the engine is created. This blocks
            # pipeline creation until a file is downloaded.
            update_on_start = True,
            # Continue to check for updates once the pipeline is running.
            auto_update = True,
            # Reload automatically when the data file on disk changes.
            file_system_watcher = True,
            data_update_product_type = DATA_UPDATE_PRODUCT_TYPE,
            usage_sharing = False).add_logger(logger).build()

        # Block until the start-up update check is complete.
        update_event.wait()
        output(f"Update on start-up complete - status - {update_event.status}")

        if update_event.status == UpdateStatus.AUTO_UPDATE_SUCCESS:
            output("Modifying downloaded file to trigger reload - please wait "
                   "for that to complete")
            update_event.clear()

            # Touching the file metadata triggers the filesystem watcher,
            # demonstrating reload when a new file is dropped into place.
            now = datetime.now().timestamp()
            try:
                os.utime(data_file, (now, now))
            except OSError:
                raise Exception("Could not modify file time, abandoning example")

            if update_event.wait(120):
                output(f"Update on file modification complete, status: "
                       f"{update_event.status}")
            else:
                output("Update on file modification timed out")
        else:
            logger.log("error", "Auto update was not successful, abandoning example")
            error_message = f"Auto update failed: {update_event.status}"
            if update_event.status == UpdateStatus.AUTO_UPDATE_ERR_429_TOO_MANY_ATTEMPTS:
                output(error_message)
            else:
                raise Exception(error_message)

        output("Finished Example")


def main(argv):
    license_key = argv[0] if len(argv) > 0 else None
    data_file = argv[1] if len(argv) > 1 else None

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    DataFileUpdateConsole().run(data_file, license_key, True, logger, print)

if __name__ == "__main__":
    main(sys.argv[1:])

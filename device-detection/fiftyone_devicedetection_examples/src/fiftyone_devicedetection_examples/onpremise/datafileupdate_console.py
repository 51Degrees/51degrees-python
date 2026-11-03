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
#
# This example illustrates various parameters that can be adjusted when using the on-premise
# device detection engine, and controls when a new data file is sought and when it is loaded by
# the device detection software.
#
# Three main aspects are demonstrated:
# - Update on Start-Up
# - Filesystem Watcher
# - Daily auto-update
#
# ## License Key
# In order to test this example you will need a 51Degrees Enterprise license which can be
# purchased from our [pricing page](https://51degrees.com/pricing/annual?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-datafileupdate_console.py&utm_term=top). Look for our "Bigger" or
# "Biggest" options.
#
# # Data Files
# You can find out more about data files, licenses etc. at our [FAQ page](https://51degrees.com/resources/faqs?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-datafileupdate_console.py&utm_term=top)
#
# ## Enterprise Data File
# Enterprise (fully-featured) data files are typically released by 51Degrees four days a week
# (Mon-Thu) and on-premise deployments can fetch and download those files automatically. Equally,
# customers may choose to download the files themselves and move them into place to be detected
# by the 51Degrees filesystem watcher.
#
# ### Manual Download
# If you prefer to download files yourself, you may do so here:
# ```
# https://distributor.51degrees.com/api/v2/download?LicenseKeys=<your_license_key>&Type=27&Download=True&Product=22
# ```
#
# ## Lite Data File
# Lite data files (free-to-use, limited capabilities, no license key required) are created roughly
# once a month and cannot be updated using auto-update, they may be downloaded from
# [Github](https://github.com/51Degrees/device-detection-data) and are included with
# source distributions of this software.
#
# # Update on Start-Up
# You can configure the pipeline builder to download an Enterprise data file on start-up.
# ## Pre-Requisites
# - a license key
# - a file location for the download
#      - this may be an existing file - which will be overwritten
#      - or if it does not exist must end in ".hash" and must be in an existing directory
# ## Configuration
# - the pipeline must be configured to use a temp file
# ``` {py}
#      create_temp_copy = True,
# ```
# - a DataFileUpdateService must be supplied
# ``` {py}
#      update_event = UpdateEvent()
#      update_service = DataFileUpdateService()
#      update_service.on_complete(lambda status, file: update_event.set(status))
#  ...
#      data_file_update_service = update_service,
# ```
# - update on start-up must be specified, which will cause pipeline creation to block until a
# file is downloaded
# ``` {py}
#      update_on_start = True,
# ```
#
# # File System Watcher
# You can configure the pipeline builder to watch for changes to the currently loaded device
# detection data file, and to replace the file currently in use with the new one. This is
# useful, for example, if you wish to download and update the device detection file "manually" -
# i.e. you would download it then drop it into place with the same path as the currently loaded
# file. That location is checked periodically (by default every 30 mins) and this frequency can be
# configured.
#
# ## Pre-Requisites
# - a license key
# - the file location of the existing file
# ## Configuration
# - the pipeline must be configured to use a temp file
# ``` {py}
#      create_temp_copy = True,
# ```
# - a DataFileUpdateService must be supplied
# ``` {py}
#      update_event = UpdateEvent()
#      update_service = DataFileUpdateService()
#      update_service.on_complete(lambda status, file: update_event.set(status))
#  ...
#      data_file_update_service = update_service,
# ```
# - configure the frequency with which the location is checked, in seconds (10 mins as shown)
# ``` {py}
#      polling_interval = (10*60),
# ```
#
# ## Daily auto-update
# Enterprise data files are usually created four times a week. Each data file contains a date
# for when the next data file is expected. You can configure the pipeline so that it starts
# looking for a newer data file after that time, by connecting to the 51Degrees distributor to
# see if an update is available. If one is, then it is downloaded and will replace the existing
# device detection file, which is currently in use.
#
# ## Pre-Requisites
# - a license key
# - the file location of the existing file
# ## Configuration
# - the pipeline must be configured to use a temp file
# ``` {py}
#      create_temp_copy = True,
# ```
# - a DataFileUpdateService must be supplied
# ``` {py}
#      update_event = UpdateEvent()
#      update_service = DataFileUpdateService()
#      update_service.on_complete(lambda status, file: update_event.set(status))
#  ...
#      data_file_update_service = update_service,
# ```
# - Set the frequency in seconds that the pipeline should check for updates to data files.
# A recommended polling interval in a production environment is around 30 minutes.
# ``` {py}
#      polling_interval = (10*60),
# ```
# - Set the max amount of time in seconds that should be added to the polling interval. This is
# useful in datacenter applications where multiple instances may be polling for  updates at the
# same time. A recommended ammount in production  environments is 600 seconds.
# ``` {py}
#      update_time_maximum_randomisation = (10*60),
# ```
#
# # Location
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/onpremise/datafileupdate_console.py).
#
# @include{doc} example-require-licensekey.txt
#
# # Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
#

import os
import shutil
import sys
import threading
from datetime import datetime

from fiftyone_devicedetection.devicedetection_pipelinebuilder import DeviceDetectionPipelineBuilder
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.key_utils import KeyUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_devicedetection_shared.example_constants import ENTERPRISE_DATAFILE_NAME
from fiftyone_pipeline_engines.datafile_update_service import DataFileUpdateService
from fiftyone_pipeline_engines.datafile_update_service import UpdateStatus

UPDATE_EXAMPLE_LICENSE_KEY_NAME = "license_key"
DEFAULT_DATA_FILENAME = os.path.expanduser("~") + os.path.sep +  ENTERPRISE_DATAFILE_NAME


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

		# try to find a license key
		if not license_key:
			license_key = KeyUtils.get_named_key(UPDATE_EXAMPLE_LICENSE_KEY_NAME)

		if not license_key:
			logger.log("error",
				"In order to test this example you will need a 51Degrees Enterprise "
				"license which can be obtained on a trial basis or purchased from our\n"
				"pricing page https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-datafileupdate_console.py&utm_term=license-key-required. You must supply the license "
				"key as an argument to this program, or as an environment or system variable "
				f"named '{UPDATE_EXAMPLE_LICENSE_KEY_NAME}'")
			raise Exception("No license key available")

		# work out where the downloaded file will be put, directory must exist
		if (data_file != None):
			try:
				data_file = ExampleUtils.find_file(data_file)
			except:
				if (os.path.exists(os.path.dirname(data_file)) == False):
					logger.log("error",
						"The directory must exist when specifying a location for a new "
						f"file to be downloaded. Path specified was '{data_file}'")
				raise Exception("Directory for new file must exist")
			logger.log("warning",
				f"File {data_file} not found, a file will be downloaded to that location on "
				"start-up")

		# no filename specified use the default
		if (data_file == None):
			data_file = os.path.realpath(DEFAULT_DATA_FILENAME)
			logger.log("warning",
				f"No filename specified. Using default '{data_file}' which will be downloaded to "
				"that location on start-up, if it does not exist already")

		copy_data_file_name = data_file + ".bak"
		if (os.path.exists(data_file)):
			# let's check this file out
			pipeline = DeviceDetectionPipelineBuilder(
				data_file_path = data_file,
				performance_profile = "LowMemory",
				usage_sharing = False,
				auto_update = False,
				licence_keys = "").add_logger(logger).build()

			# and output the results
			ExampleUtils.check_data_file(pipeline, logger)
			if (ExampleUtils.get_data_file_tier(pipeline.get_element("device")) == "Lite"):
				logger.log("error",
					"Will not download an 'Enterprise' data file over the top of "
					"a 'Lite' data file, please supply another location.")
				raise Exception("File supplied has wrong data tier")
			logger.log("info", "Existing data file will be replaced with downloaded data file")
			logger.log("info", f"Existing data file will be copied to {copy_data_file_name}")

		# do we really want to do this
		if (interactive):
			output("Please note - this example will use available downloads "
				"in your licensed allocation.")
			user_input = input("Do you wish to continue with this example (y)? ")
			if (user_input == None or user_input == "" or user_input.startswith("y") == False):
				logger.log("info", "Stopping example without download")
				return

		logger.log("info", "Checking file exists")
		if os.path.exists(data_file):
			logger.log("info", f"Existing data file copied to {copy_data_file_name}")
			shutil.copy(data_file, copy_data_file_name)

		logger.log("info",
			"Creating pipeline and initiating update on start-up - please wait for that "
			"to complete")

		update_event = UpdateEvent()
		update_service = DataFileUpdateService()
		update_service.on_complete(lambda status, file: update_event.set(status))

		# Build the device detection pipeline  and pass in the desired settings to configure
		# automatic updates.
		pipeline = DeviceDetectionPipelineBuilder(
			# specify the filename for the data file. When using update on start-up
			# the file need not exist, but the directory it is in must exist.
			# Any file that is present is overwritten. Because the file will be
			# overwritten the pipeline must be configured to copy the supplied
			# file to a temporary file (create_temp_copy parameter == True).
			data_file_path = data_file,
			create_temp_copy = True,
			# pass in the update listener which has been configured
			# to notify when update complete
			data_file_update_service = update_service,
			# For automatic updates to work you will need to provide a license key.
			# A license key can be obtained with a subscription from https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-datafileupdate_console.py&utm_term=run
			licence_keys = license_key,
			# Enable update on startup, the auto update system
			# will be used to check for an update before the
			# device detection engine is created. This will block
			# creation of the pipeline.
			update_on_start = True,
			# Enable automatic updates once the pipeline has started
			auto_update = True,
			# Watch the data file on disk and refresh the engine
			# as soon as that file is updated.
			file_system_watcher=True,
			data_update_product_type="V4Enterprise",
			).add_logger(logger).build()


		# thread blocks till update checking is complete - or if there is an
		# exception we don't get this far
		update_event.wait()
		output(f"Update on start-up complete - status - {update_event.status}")

		if update_event.status == UpdateStatus.AUTO_UPDATE_SUCCESS:

			output("Modifying downloaded file to trigger reload - please wait for that"
				" to complete")

			# wait for the dataUpdateService to notify us that it has updated
			update_event.clear()

			# it's the same file but changing the file metadata will trigger reload,
			# demonstrating that if you download a new file and replace the
			# existing one, then it will be loaded
			now = datetime.now().timestamp()
			try:
				os.utime(data_file, (now, now))
			except:
				raise Exception("Could not modify file time, abandoning "
					"example")

			if update_event.wait(120):
				output(f"Update on file modification complete, status: {update_event.status}")
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
	# Use the supplied path for the data file or find the lite
	# file that is included in the repository.
	license_key = argv[0] if len(argv) > 0 else None
	data_file = argv[1] if len(argv) > 1 else None

	# Configure a logger to output to the console.
	logger = Logger(min_level="info")

	DataFileUpdateConsole().run(data_file, license_key, True, logger, print)

if __name__ == "__main__":
	main(sys.argv[1:])

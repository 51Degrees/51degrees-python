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

from fiftyone_devicedetection.devicedetection_pipelinebuilder import DeviceDetectionPipelineBuilder

# First create the device detection pipeline with the desired settings.

data_file = "../fiftyone_devicedetection_onpremise/src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/51Degrees-LiteV4.1.hash"
resource_key = "!!YOUR_RESOURCE_KEY!!"

# Uncommment the line below 'On-Premise' and comment the line below 'Cloud' to 
# switch to an On-Premise installation
# On-Premise
pipeline = DeviceDetectionPipelineBuilder(data_file_path = data_file, licence_keys = "", performance_profile = 'MaxPerformance', auto_update=False).build()

# Cloud
#pipeline = DeviceDetectionPipelineBuilder({"resource_key": resource_key}).build()

# We create a FlowData object from the pipeline
# this is used to add evidence to and then process

flowdata1 = pipeline.create_flowdata()

# Here we add a User-Agent of a desktop as evidence

desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"

flowdata1.evidence.add("header.user-agent", desktop_ua)

# Now we process the FlowData

flowdata1.process()

# To check whether the User-Agent is a mobile device we look at the ismobile property
# inside the Device Detection Engine

# first we check if this has a meaningful result

print("Is User-Agent " + desktop_ua + " a mobile? ") 
if flowdata1.device.ismobile.has_value():
    print(flowdata1.device.ismobile.value())
else:
    # Output why the value isn't meaningful
    print(flowdata1.device.ismobile.no_value_message())

# Now we do the same with a new User-Agent, this time from an iphone

flowdata2 = pipeline.create_flowdata()

iphone_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"

flowdata2.evidence.add("header.user-agent", iphone_ua)

flowdata2.process()

print("Is User-Agent " + iphone_ua + " a mobile device?: ") 
if flowdata2.device.ismobile.has_value():
    print(flowdata2.device.ismobile.value())
else:
    # Output why the value isn't meaningful
    print(flowdata2.device.ismobile.no_value_message())

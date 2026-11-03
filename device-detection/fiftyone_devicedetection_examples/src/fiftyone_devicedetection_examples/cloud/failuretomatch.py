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

from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder

# First create the device detection pipeline with the desired settings.

# You need to create a resource key at https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-failuretomatch.py&utm_term=top
# and paste it into the code, replacing !!YOUR_RESOURCE_KEY!! below.
# Alternatively, set the _51DEGREES_RESOURCE_KEY environment variable. The
# key is read through ExampleUtils, as every other example reads it, so
# this one answers to the same variable names as the rest and a reader who
# has set one of them does not have to work out why only this example says
# it has no key.
from fiftyone_devicedetection_examples.example_utils import ExampleUtils

resource_key = ExampleUtils.get_resource_key() or "!!YOUR_RESOURCE_KEY!!"

if resource_key == "!!YOUR_RESOURCE_KEY!!":
    print(ExampleUtils.get_missing_resource_key_message())
    # The address stays on one line, because the campaign lint reads a
    # line at a time and a split address looks to it like a missing tag.
    print("    To include the properties used in this example, go to "
          "https://configure.51degrees.com/bxXqZhLT?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-failuretomatch.py&utm_term=resource-key-required")
else:

    pipeline = DeviceDetectionCloudPipelineBuilder({
        "resource_key": resource_key
    }).build()

    # We create a FlowData object from the pipeline
    # this is used to add evidence to and then process

    flowdata1 = pipeline.create_flowdata()

    # Here we add a User-Agent of an iphone as evidence

    iphone_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Mobile/15C114"
    
    flowdata1.evidence.add("header.user-agent", iphone_ua)

    # Now we process the FlowData

    flowdata1.process()

    # To check whether the User-Agent is a mobile device we look at the ismobile property
    # inside the Device Detection Engine

    # first we check if this has a meaningful result

    print("Is User-Agent " + iphone_ua + " a mobile device?: ") 
    if flowdata1.device.ismobile.has_value():
        print(flowdata1.device.ismobile.value())
    else:
        # Output why the value isn't meaningful
        print(flowdata1.device.ismobile.no_value_message())

    # Now we do the same with a new User-Agent, this time a corrupted one

    badUA = "--"
    
    flowdata2 = pipeline.create_flowdata()

    flowdata2.evidence.add("header.user-agent", badUA)

    flowdata2.process()

    print("Is User-Agent " + badUA + " a mobile device?: ") 
    if flowdata2.device.ismobile.has_value():
        print(flowdata2.device.ismobile.value())
    else:
        # Output why the value isn't meaningful
        print(flowdata2.device.ismobile.no_value_message())

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
## @example onpremise/performance.py
# 
# Provides an example of processing a CSV file containing evidence for device detection. 
# There are 20,000 examples in the supplied file of evidence representing HTTP Headers.
# For example:
# 
# We create a device detection pipeline to read the data and output the time taken and information about about the detection.
# 
# Requesting properties from a single component
# reduces detection time compared with requesting properties from multiple components. If you
# don't specify any properties to detect, then all properties are detected.
#
# Please review [performance options](/documentation/4.5/_device_detection__features__performance_options.html)
# and [hash dataset options](/documentation/4.5/_device_detection__hash.html#DeviceDetection_Hash_DataSetProduction_Performance)
# for more information about adjusting performance.
# 
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/onpremise/performance.py). 
# 
# @include{doc} example-require-datafile.txt
# 
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)

import argparse
import csv
import json
import time
import multiprocessing as mp

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
# This example goes through a CSV of 20000 user agents and processes them, returning the time and information about the matches
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder

# Here we make a function that processes a user agent
# And returns if it is a mobile device

# global variables will be assigned later in the main block:
threads = 0
split_lists = None


def process_user_agent(user_agent):

    # First we create the flowdata using the global pipeline
    flowdata = pipeline.create_flowdata()  # pylint: disable=used-before-assignment

    # Here we add the user agent as evidence
    flowdata.evidence.add("header.user-agent", user_agent)

    # We process the flowdata to get the results
    flowdata.process()

    # To check whether the User-Agent is a mobile device we look at the ismobile
    # property inside the Device Detection Engine

    # first we check if this has a meaningful result

    if flowdata.device.ismobile.has_value():
        return flowdata.device.ismobile.value()
    else:
        return None

def process_user_agent_list(data_file, user_agent_list, list_number, output, skip=False):
    global pipeline
    pipeline = DeviceDetectionOnPremisePipelineBuilder(
        data_file_path=data_file,
        licence_keys="",
        performance_profile='MaxPerformance',
        add_javascript_builder=False,
        restricted_properties=["ismobile"],
        usage_sharing=False,
        auto_update=False).build()

    results = {
        "mobile": 0,
        "notmobile": 0,
        "unknown": 0
    }
    for user_agent in user_agent_list:
        if skip:
            break
        result = process_user_agent(user_agent[0])
        if(result == None):
            results["unknown"] += 1
        if(result == True):
            results["mobile"] += 1
        if(result == False):
            results["notmobile"] += 1

    output.put(results, list_number)

# Run the process
def run(data_file, skip = False):
    # Make a queue to store the results in

    output = mp.Queue()

    # Create processes
    processes = []

    for x in range(threads):  # pylint: disable=used-before-assignment
        processes.append(mp.Process(target=process_user_agent_list,
                                    args=(data_file, split_lists[x], x, output, skip)))  # pylint: disable=used-before-assignment

    # Start timer

    t0 = time.time()

    for p in processes:
        p.start()

    # Exit the completed processes
    for p in processes:
        p.join()

    # Get process results from the output queue
    results = [output.get() for p in processes]

    t1 = time.time()
    total = t1-t0

    return {"time": total, "result": results}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Run detection benchmark.')
    ap.add_argument('-d', '--data_file', default='', help='Path to data file')
    ap.add_argument('-u', '--user_agents_file', default='src/fiftyone_devicedetection_onpremise/cxx/device-detection-data/20000 User Agents.csv', help='Path to user agents evidence file')
    ap.add_argument('-j', '--json_output', default='', help='Output results in JSON format')
    args = ap.parse_args()
    if args.data_file == "":
        args.data_file = ExampleUtils.find_file("51Degrees-LiteV4.1.hash")

    # First we read the contents of the 20000 user agents file as a list
    with open(args.user_agents_file, newline='') as file:
        reader = csv.reader(file)
        user_agents = list(reader)

    number_of_user_agents = len(user_agents)

    print("Processing " + str(number_of_user_agents) + " user agents")

    # Now we make a function that returns results of the user agent matching

    threads = mp.cpu_count()

    print("Using " + str(threads) + " threads")

    chunk_size = int(number_of_user_agents / threads)

    # Split lists by number of threads
    split_lists = [user_agents[x:x+chunk_size]
                for x in range(0, len(user_agents), chunk_size)]

    calibration = run(args.data_file, skip=True)

    real = run(args.data_file, skip=False)

    real_time = real["time"]

    print("Total time (seconds): " + str(real_time) + " seconds")
    print("Time per user agent (ms): " + str((real_time / number_of_user_agents) * 1000))

    if args.json_output != "":
        results = {
            "DetectionsPerSecond": 1.0 / (real_time / number_of_user_agents),
            "MsPerDetection": real_time * 1000 / number_of_user_agents
        }
        with open(args.json_output, "w") as file:
            print(json.dumps(results), file = file)

    final_result = {
        "mobile": 0,
        "notmobile": 0,
        "unknown": 0
    }

    for result in real["result"]:
        final_result["unknown"] += result["unknown"]
        final_result["mobile"] += result["mobile"]
        final_result["notmobile"] += result["notmobile"]

    print("Results", final_result)

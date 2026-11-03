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

import sys
import json
import argparse
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from flask import Flask, request
from timeit import timeit

# Helper function to get a property value if it exists and return 
# the reason why if it doesn't
def getValueHelper(flowdata, engine, propertyKey):
    engineProperties = getattr(flowdata, engine)
    try:
        propertyValue = getattr(engineProperties, propertyKey)
        if propertyValue.has_value():
            return propertyValue.value()
        else:
            return propertyValue.no_value_message()
    except:
        return "Not found in datafile"

def detect(app, pipeline, user_agents):
    with app.test_request_context("/process", headers=(("User-Agent", next(user_agents)),)):
        # Without remote_addr in request object we'd get:
        # ValueError: invalid null reference in method 'MapStringStringSwig___setitem__', argument 3 of type 'std::map< std::string,std::string >::mapped_type const &'
        # in flowdata.process(). This mock-request doesn't set it, so we set it manually
        request.remote_addr = "127.0.0.1"

        flowdata = pipeline.create_flowdata()

        # Add any information from the request (headers, cookies and additional 
        # client side provided information)
        flowdata.evidence.add_from_dict(webevidence(request))

        # Process the flowdata
        flowdata.process()

        return getValueHelper(flowdata, "device", "ismobile")

def benchmark(data_file, user_agents_file, output=False):
    app = Flask(__name__)

    # Create Device Detection pipeline using datafile
    pipeline = DeviceDetectionOnPremisePipelineBuilder(
        data_file_path = data_file, 
        licence_keys = "", 
        performance_profile = "MaxPerformance", 
        update_on_start = False,
        usage_sharing = False,
        restricted_properties = [ "IsMobile" ], 
        settings = { "add_javascript_builder": False },
    ).build()

    with open(user_agents_file) as f:
        user_agents_list = [ua.rstrip() for ua in f]
    user_agents = iter(user_agents_list)

    print(f"Benchmarking with {len(user_agents_list)} user agents", file=sys.stderr)
    environment = {"detect": detect, "app": app, "pipeline": pipeline, "user_agents": user_agents}
    time = timeit("detect(app, pipeline, user_agents)", globals=environment, number=len(user_agents_list))

    if output:
        json.dump({
            "Detections": len(user_agents_list),
            "DetectionsPerSecond": len(user_agents_list) / time,
            "RuntimeSeconds": time,
            "AvgMillisecsPerDetection": time / len(user_agents_list) * 1000,
        }, sys.stdout, indent=4)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Run detection benchmark.')
    ap.add_argument('data_file', help='Path to data file')
    ap.add_argument('user_agents_file', help='Path to user agents evidence file')
    ap.add_argument('-o', '--output', action='store_true', help='Output results in JSON format')
    args = ap.parse_args()

    benchmark(args.data_file, args.user_agents_file, args.output)

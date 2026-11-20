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

# Times IP Intelligence lookups made from web requests, in the same form as
# the Device Detection benchmark in
# device-detection/fiftyone_devicedetection_examples/performance-tests. Each
# IP address in the evidence file is made the client address of a mock Flask
# request, whose evidence the pipeline then processes. The performance step
# runs it on the free Lite data file, so it needs no licensed file.

import sys
import json
import argparse
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder
from fiftyone_pipeline_core.web import webevidence
from flask import Flask, request
from ruamel.yaml import YAML
from timeit import timeit

# The evidence file gives each IP address under this key.
CLIENT_IP = "server.client-ip"

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

def detect(app, pipeline, ip_addresses):
    # The IP address is the client address of the mock request, which
    # webevidence gives as server.client-ip.
    with app.test_request_context(
            "/process", environ_base={"REMOTE_ADDR": next(ip_addresses)}):

        # The FlowData is closed when the function returns, which releases
        # the results of the lookup straight away.
        with pipeline.create_flowdata() as flowdata:

            # Add any information from the request (headers, cookies and additional
            # client side provided information)
            flowdata.evidence.add_from_dict(webevidence(request))

            # Process the flowdata
            flowdata.process()

            return getValueHelper(flowdata, "ip", "registeredcountry")

def load_ip_addresses(evidence_file):
    # Each record in the evidence file is a YAML document of its own.
    yaml = YAML(typ="safe")
    with open(evidence_file) as f:
        return [str(record[CLIENT_IP]) for record in yaml.load_all(f)
                if record and CLIENT_IP in record]

def benchmark(data_file, evidence_file, output=False):
    app = Flask(__name__)

    # Create IP Intelligence pipeline using datafile
    pipeline = IpIntelligenceOnPremisePipelineBuilder(
        data_file_path = data_file,
        licence_keys = "",
        performance_profile = "MaxPerformance",
        auto_update = False,
        update_on_start = False,
        # The data file is used in place, rather than through a temporary
        # copy of a file of hundreds of megabytes.
        create_temp_data_copy = False,
        usage_sharing = False,
        settings = { "add_javascript_builder": False },
    ).build()

    # The pipeline is closed once the lookups have been timed, which
    # releases the native data it holds.
    with pipeline:
        ip_addresses_list = load_ip_addresses(evidence_file)
        ip_addresses = iter(ip_addresses_list)

        print(f"Benchmarking with {len(ip_addresses_list)} IP addresses", file=sys.stderr)
        environment = {"detect": detect, "app": app, "pipeline": pipeline, "ip_addresses": ip_addresses}
        time = timeit("detect(app, pipeline, ip_addresses)", globals=environment, number=len(ip_addresses_list))

    if output:
        json.dump({
            "Detections": len(ip_addresses_list),
            "DetectionsPerSecond": len(ip_addresses_list) / time,
            "RuntimeSeconds": time,
            "AvgMillisecsPerDetection": time / len(ip_addresses_list) * 1000,
        }, sys.stdout, indent=4)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Run IP Intelligence lookup benchmark.')
    ap.add_argument('data_file', help='Path to data file')
    ap.add_argument('evidence_file', help='Path to YAML evidence file of IP addresses')
    ap.add_argument('-o', '--output', action='store_true', help='Output results in JSON format')
    args = ap.parse_args()

    benchmark(args.data_file, args.evidence_file, args.output)

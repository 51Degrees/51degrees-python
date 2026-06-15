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

## @example onpremise/gettingstarted_web/app.py
# @brief Getting Started Web Example - On-premise
#
# A simple Flask web application that resolves the IP address of the
# visitor (or an IP supplied as the "client-ip" query parameter) using
# the on-premise IP intelligence engine.
#
# Run with:
# ```
# python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_web
# ```

from flask import Flask, request

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.example_constants import LITE_DATAFILE_NAME

app = Flask(__name__)

pipeline = None


def build_pipeline(data_file):
    global pipeline
    pipeline = IpIntelligencePipelineBuilder(
        data_file_path = data_file,
        performance_profile = "LowMemory",
        usage_sharing = False,
        auto_update = False,
        licence_keys = "").build()
    return pipeline


def get_value(ip_data, property):
    return ExampleUtils.get_human_readable(ip_data, property)


@app.route("/")
def index():

    # Create the flowdata object for this request.
    flowdata = pipeline.create_flowdata()

    # Use the IP address supplied as a query parameter, or fall back
    # to the address of the requester.
    client_ip = request.args.get("client-ip", request.remote_addr)

    flowdata.evidence.add("query.client-ip", client_ip)

    # Process the flowdata
    flowdata.process()

    ip_data = flowdata.ip

    return f"""
    <h2>51Degrees IP Intelligence - Getting Started Web (On-Premise)</h2>
    <p>IP address: {client_ip}</p>
    <ul>
        <li>Registered Name: {get_value(ip_data, "registeredname")}</li>
        <li>Registered Owner: {get_value(ip_data, "registeredowner")}</li>
        <li>Registered Country: {get_value(ip_data, "registeredcountry")}</li>
    </ul>
    <p>Add ?client-ip=x.x.x.x to the url to lookup a different address.</p>
    """


def main(data_file = None):
    if not data_file:
        data_file = ExampleUtils.find_file(LITE_DATAFILE_NAME)
    if not data_file:
        raise Exception(
            "Failed to find an IP intelligence data file. Download the "
            "Lite file from https://51ddatafiles.blob.core.windows.net/"
            "enterpriseipi/51Degrees-LiteIpiV41.ipi.gz")
    build_pipeline(data_file)
    app.run(debug=False)


if __name__ == "__main__":
    main()

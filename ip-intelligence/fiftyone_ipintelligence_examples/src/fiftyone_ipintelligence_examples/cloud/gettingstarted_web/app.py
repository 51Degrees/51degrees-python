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

## @example cloud/gettingstarted_web/app.py
# @brief Getting Started Web Example - Cloud
#
# A simple Flask web application that resolves the IP address of the
# visitor (or an IP supplied as the "client-ip" query parameter) using
# the 51Degrees cloud service.
#
# A resource key must be supplied in the `_51DEGREES_RESOURCE_KEY` environment
# variable. Obtain one from https://51degrees.com/configure/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_web-app.py&utm_term=top
#
# Run with:
# ```
# python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_web
# ```

from flask import Flask, request

from fiftyone_pipeline_core.web import webevidence
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.constants import Constants

# Where to go next, shown at the end of the page.
FIND_OUT_MORE = [
    ("IP intelligence",
     "https://51degrees.com/ip-intelligence?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_web-app.py&utm_term=find-out-more-ip-intelligence"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_web-app.py&utm_term=find-out-more-resource-keys"),
    ("Pricing",
     "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_web-app.py&utm_term=find-out-more-pricing"),
    ("IP intelligence for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/ip-intelligence"),
]

app = Flask(__name__)

pipeline = None


def build_pipeline(resource_key):
    global pipeline
    pipeline = IpIntelligencePipelineBuilder(
        resource_key = resource_key).build()
    return pipeline


def get_value(ip_data, property):
    return ExampleUtils.get_human_readable(ip_data, property)


@app.route("/")
def index():

    # Create the flowdata object for this request.
    flowdata = pipeline.create_flowdata()

    # Hand the whole request to the pipeline. Each engine takes the
    # Evidence it reads from it, and usage sharing takes the request.
    flowdata.evidence.add_from_dict(webevidence(request))

    # Use the IP address supplied as a query parameter, or fall back
    # to the address of the requester.
    client_ip = request.args.get("client-ip", request.remote_addr)

    flowdata.evidence.add(Constants.EVIDENCE_QUERY_CLIENT_IP_51D_KEY, client_ip)

    # Process the flowdata
    flowdata.process()

    ip_data = flowdata.ip

    return f"""
    <h2>51Degrees IP Intelligence - Getting Started Web (Cloud)</h2>
    <p>IP address: {client_ip}</p>
    <ul>
        <li>Registered Name: {get_value(ip_data, "registeredname")}</li>
        <li>Registered Country: {get_value(ip_data, "registeredcountry")}</li>
    </ul>
    <p>Add ?client-ip=x.x.x.x to the url to lookup a different address.</p>
    {ExampleUtils.get_find_out_more_html(FIND_OUT_MORE)}
    """


def main(resource_key = None):
    if not resource_key:
        resource_key = ExampleUtils.get_resource_key()
    if not resource_key:
        raise Exception(
            "No resource key specified in the environment variable "
            f"'{ExampleUtils.CLOUD_RESOURCE_KEY_ENV_VAR}'. Obtain one from "
            "https://51degrees.com/configure/?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-cloud-gettingstarted_web-app.py&utm_term=resource-key-required")
    build_pipeline(resource_key)
    app.run(debug=False)

    # The server has stopped, which is the example's end.
    ExampleUtils.print_find_out_more(FIND_OUT_MORE)


if __name__ == "__main__":
    main()

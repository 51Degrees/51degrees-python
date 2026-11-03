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


## @example cloud/useragentclienthints_web/app.py
#
# This example demonstrates how a User-Agent Client Hints (UACH) round trip works
# with the 51Degrees cloud service. By default the user-agent, sec-ch-ua and
# sec-ch-ua-mobile HTTP headers are sent. If device detection determines that the
# browser supports client hints then it requests additional client hints headers by
# setting the Accept-CH header in the response. Selecting the "Make second request"
# button reloads the page so those additional headers are included as evidence.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/cloud/useragentclienthints_web/app.py).
#
# @include{doc} example-require-resourcekey.txt
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection_cloud](https://pypi.org/project/fiftyone-devicedetection-cloud/)
# - [flask](https://pypi.org/project/flask/)
#
# ## View
# @include templates/index.html
#
# ## App

import os
import sys
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from flask import Flask, request, render_template
from flask.helpers import make_response
from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.web import webevidence, set_response_header


class UserAgentClientHintsWeb():
    app = Flask(__name__)

    def build(self, resource_key, logger):
        # First create the device detection pipeline with the desired settings.
        # The cloud service is configured with the required UACH SetHeader properties
        # which follow the format SetHeader[Component name][Response header name],
        # e.g. for browser component properties to be set in the Accept-CH response
        # header use the SetHeaderBrowserAccept-CH property.
        pipeline_settings = {
            "resource_key": resource_key,
            # Set to True so a device-detection failure degrades gracefully instead of
            # returning a 500 for every request. Use False while developing to surface
            # mistakes loudly. Errors are still recorded on flowdata.errors / the logger.
            "suppress_process_exceptions": True,
        }
        # If a cloud endpoint is set in the environment, point the pipeline at it.
        cloud_endpoint = ExampleUtils.get_cloud_endpoint()
        if cloud_endpoint:
            pipeline_settings["cloud_endpoint"] = cloud_endpoint

        UserAgentClientHintsWeb.pipeline = DeviceDetectionCloudPipelineBuilder(
            pipeline_settings).add_logger(logger).build()

        return self

    def run(self):
        UserAgentClientHintsWeb.app.run(port=int(os.environ.get("PORT", 5000)))

    # The main route performs device detection and renders the results. On the
    # second request, any additional client hints headers requested via the
    # Accept-CH response header from the first request will be included as evidence.

    @staticmethod
    @app.route('/')
    def server():

        # Create the flowdata object for the device detection
        flowdata = UserAgentClientHintsWeb.pipeline.create_flowdata()

        # Add any information from the request (headers, cookies and any other
        # additional information)
        flowdata.evidence.add_from_dict(webevidence(request))

        # Process the flowdata
        flowdata.process()

        response = make_response()

        # Some browsers require that extra HTTP headers are explicitly
        # requested. So set whatever headers are required by the browser in
        # order to return the evidence needed by the pipeline.
        # More info on this can be found at
        # https://51degrees.com/blog/user-agent-client-hints?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-useragentclienthints_web-app.py&utm_term=server
        set_response_header(flowdata, response)

        # Generate the HTML
        response.set_data(render_template(
            'index.html',
            data=flowdata,
            utils=ExampleUtils,
            response=response))

        return response


def main(argv):
    # Use the command line args to get the resource key if present.
    # Otherwise, get it from the environment variable.
    resource_key = argv[0] if len(argv) > 0 else ExampleUtils.get_resource_key()

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (resource_key):
        UserAgentClientHintsWeb().build(resource_key, logger).run()

    else:
        logger.log("error",
            "No resource key specified in environment variable " +
            f"'{ExampleUtils.RESOURCE_KEY_ENV_VAR}'. The 51Degrees " +
            "cloud service is accessed using a 'ResourceKey'. " +
            "For more detail see " +
            "https://51degrees.com/documentation/_info__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-useragentclienthints_web-app.py&utm_term=resource-key-required. " +
            "A resource key with the properties required by this " +
            "example can be created for free at " +
            "https://configure.51degrees.com/?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-cloud-useragentclienthints_web-app.py&utm_term=resource-key-required. " +
            "Once complete, populated the environment variable " +
            "mentioned at the start of this message with the key.")


if __name__ == "__main__":
    main(sys.argv[1:])

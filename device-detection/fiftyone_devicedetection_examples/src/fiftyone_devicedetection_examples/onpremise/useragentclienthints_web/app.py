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


## @example onpremise/useragentclienthints_web/app.py
#
# This example demonstrates how a User-Agent Client Hints (UACH) round trip works
# with the 51Degrees on-premise device detection API. By default the user-agent,
# sec-ch-ua and sec-ch-ua-mobile HTTP headers are sent. If device detection determines
# that the browser supports client hints then it requests additional client hints
# headers by setting the Accept-CH header in the response. Selecting the "Make second
# request" button reloads the page so those additional headers are included as evidence.
#
# The pipeline is configured with the required UACH properties that follow the format
# SetHeader[Component name][Response header name], e.g. for browser, platform and hardware
# component properties to be set in the Accept-CH response header include
# SetHeaderBrowserAccept-CH, SetHeaderPlatformAccept-CH and SetHeaderHardwareAccept-CH
# properties respectively.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/onpremise/useragentclienthints_web/app.py).
#
# @include{doc} example-require-datafile.txt
#
# Required PyPi Dependencies:
# - [fiftyone_devicedetection_onpremise](https://pypi.org/project/fiftyone-devicedetection-onpremise/)
# - [flask](https://pypi.org/project/flask/)
#
# ## View
# @include templates/index.html
#
# ## App

import os
from pathlib import Path
import sys
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from flask import Flask, request, render_template
from flask.helpers import make_response
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import webevidence, set_response_header
import json


class UserAgentClientHintsWeb():
    app = Flask(__name__)

    def build(self, config, logger):
        # 'suppress_process_exceptions' is set to True in config.json
        # (PipelineOptions.BuildParameters) so a device-detection failure degrades
        # gracefully instead of returning a 500 for every request. Use False while
        # developing to surface mistakes loudly.
        UserAgentClientHintsWeb.pipeline = PipelineBuilder().add_logger(logger).build_from_configuration(config)
        return self

    def run(self):
        UserAgentClientHintsWeb.app.run(port=5001)

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
        # https://51degrees.com/blog/user-agent-client-hints?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-useragentclienthints_web-app.py&utm_term=server
        set_response_header(flowdata, response)

        # Generate the HTML
        response.set_data(render_template(
            'index.html',
            data=flowdata,
            utils=ExampleUtils,
            response=response))

        return response

    # Typically, something like this will not be necessary.
    # The device detection API will accept an absolute or relative path for the data file.
    # However, if a relative path is specified, it will only look in the current working
    # directory.
    # In our examples, we have many different projects and we don't want to have a copy of
    # the data file for every single one.
    # In order to handle this, we dynamically search the project directories for the data
    # file location and then override the configured setting with the absolute path if
    # necessary.
    # In a real-world scenario, you can just put the data file in your working directory
    # or use an absolute path in the configuration file.
    @staticmethod
    def build_config():

        # Load the configuration file
        configFile = Path(__file__).resolve().parent.joinpath("config.json").read_text()
        config = json.loads(configFile)

        dataFile = ExampleUtils.get_data_file_from_config(config)
        foundDataFile = False
        if not dataFile:
            raise Exception("A data file must be specified in the config.json file.")
        # The data file location provided in the configuration may be using an absolute or
        # relative path. If it is relative then search for a matching file using the
        # ExampleUtils.find_file function.
        elif os.path.isabs(dataFile) == False:
            newPath = ExampleUtils.find_file(dataFile)
            if newPath:
                # Add an override for the absolute path to the data file.
                ExampleUtils.set_data_file_in_config(config, newPath)
                foundDataFile = True
        else:
            foundDataFile = os.path.exists(dataFile)

        if foundDataFile == False:
            raise Exception("Failed to find a device detection data file matching " +
                f"'{dataFile}'. If using the lite file, then make sure the " +
                "device-detection-data submodule has been updated by running " +
                "`git submodule update --recursive`. Otherwise, ensure that the filename " +
                "is correct in config.json.")

        return config


def main(argv):
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    config = UserAgentClientHintsWeb.build_config()

    UserAgentClientHintsWeb().build(config, logger).run()


if __name__ == "__main__":
    main(sys.argv[1:])

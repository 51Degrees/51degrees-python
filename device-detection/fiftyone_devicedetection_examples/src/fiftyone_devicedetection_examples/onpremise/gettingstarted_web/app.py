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
#
# @include{doc} example-getting-started-web.txt
# 
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/onpremise/gettingstarted_web/app.py). 
# 
# @include{doc} example-require-datafile.txt
# 
# Required PyPi Dependencies:
# - [fiftyone_devicedetection](https://pypi.org/project/fiftyone-devicedetection/)
# - [flask](https://pypi.org/project/flask/)
# 
# ## Overview
# 
# The `DeviceDetectionPipelineBuilder` class is used to create a Pipeline instance from the configuration
# that is supplied.
# The fiftyone_pipeline_core.web module contains helpers which deal with
# automatically populating evidence from a web request.
# ```{py}
# flowdata.evidence.add_from_dict(webevidence(request))
# ```
#
# The module can also handling setting response headers (e.g. Accept-CH for User-Agent 
# Client Hints) and serving requests for client-side JavaScript and JSON resources.
# ```{py}
# set_response_header(flowdata, response)
# ```
# 
# The results of detection can be accessed by through the flowdata object once
# processed. This can then be used to interrogate the data.
# ```{py}
# flowdata.process()
# device = flowdata.device
# hardware_vendor = device.hardwarevendor
# ```
# 
# Results can also be accessed in client-side code by using the `fod` object. See the 
# [JavascriptBuilderElement](https://51degrees.com/documentation/apis/pipeline-python/classfiftyone__pipeline__core_1_1javascriptbuilder_1_1_javascript_builder_element.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-gettingstarted_web-app.py&utm_term=top)
# for details on available settings such as changing the `fod` name.
# ```{js}
# window.onload = function () {
#     fod.complete(function(data) {
#         var hardwareName = data.device.hardwarename;
#         alert(hardwareName.join(", "));
#     }
# }
# ```
#
# ## View
# @include onpremise/gettingstarted_web/templates/index.html
#
# ## App

import os
from pathlib import Path
import sys
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from flask.helpers import make_response
from flask import Flask, request, render_template
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_core.web import (
    javascript_response, json_response, webevidence, set_response_header)
import json

class GettingStartedWeb():
    app = Flask(__name__)

    def build(self, config, logger):
        # Here we add some callback settings for the page to make a request with extra evidence from the client side, in this case the Flask /json route we will make below

        # 'suppress_process_exceptions' is set to True in config.json
        # (PipelineOptions.BuildParameters) so a device-detection failure degrades
        # gracefully instead of returning a 500 for every request. Use False while
        # developing to surface mistakes loudly.
        GettingStartedWeb.pipeline = PipelineBuilder().add_logger(logger).build_from_configuration(config)
        return self

    def run(self):

        # The port can be set with the PORT environment variable, as it can
        # for the cloud example, so the example can run next to other services.
        # The pipeline lives as long as the app, and is closed when the server
        # stops, which releases the native data it holds.
        with GettingStartedWeb.pipeline:
            GettingStartedWeb.app.run(port=int(os.environ.get("PORT", 5001)))

    # First we make a JSON route that will be called from the client side and will return
    # a JSON encoded property database using any additional evidence provided by the client.
    # json_response processes the request and sets the cache headers, so a browser keeps a
    # good answer for 30 minutes and never keeps one made while processing failed.

    @staticmethod
    @app.route('/json', methods=['POST'])
    def jsonroute():

        return json_response(GettingStartedWeb.pipeline, request)

    # Next we serve the client-side JavaScript from its own route. The other
    # Pipeline APIs ship a web integration that intercepts '/51Degrees.core.js'
    # for this, so the page can reference the script by that name. There is no
    # such integration for Flask, so the example wires up the route itself.
    # Query parameters are evidence, so the per-request 'fod-js-enable-cookies'
    # override is picked up and applied by the JavaScriptBuilder engine.

    @staticmethod
    @app.route('/51Degrees.core.js')
    def core_js():

        return javascript_response(GettingStartedWeb.pipeline, request)

    # In the main route we dynamically update the screen's device property display
    # using the above JSON route

    @staticmethod
    @app.route('/')
    def server():

        # Create the flowdata object for the page. It is closed when the route
        # returns, once the page has been rendered from it.
        with GettingStartedWeb.pipeline.create_flowdata() as flowdata:

            # Add any information from the request (headers, cookies and additional 
            # client side provided information)

            flowdata.evidence.add_from_dict(webevidence(request))

            # Process the flowdata

            flowdata.process()

            response = make_response()

            # Some browsers require that extra HTTP headers are explicitly
            # requested. So set whatever headers are required by the browser in
            # order to return the evidence needed by the pipeline.
            # More info on this can be found at
            # https://51degrees.com/blog/user-agent-client-hints?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-gettingstarted_web-app.py&utm_term=server

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

        # A data file named in the _51DEGREES_DD_PATH environment variable takes
        # the place of the one in config.json. This lets the example run
        # against a paid data file without editing the configuration.
        envDataFile = ExampleUtils.get_data_file_path()
        if envDataFile:
            envDataFile = os.path.abspath(envDataFile)
            if not os.path.exists(envDataFile):
                raise Exception("The device detection data file " +
                    f"'{envDataFile}' named in the environment variable " +
                    f"'{ExampleUtils.DD_PATH_ENV_VAR}' does not exist.")
            ExampleUtils.set_data_file_in_config(config, envDataFile)
            return config

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
                "data submodule is there, by running " +
                "`git submodule update --init --recursive`, and run this " +
                "example again to download the file. Otherwise, ensure that the filename " +
                "is correct in config.json, or set the environment variable " +
                f"'{ExampleUtils.DD_PATH_ENV_VAR}' to the path of the data file.")

        return config

def main(argv):
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    config = GettingStartedWeb.build_config()

    GettingStartedWeb().build(config, logger).run()

if __name__ == "__main__":
    main(sys.argv[1:])

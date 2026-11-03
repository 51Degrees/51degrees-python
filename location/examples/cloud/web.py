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

## @example cloud/web.py
#
# This example is designed to output location data using the client-side evidence feature of the pipeline.
#
# This example uses the client-side evidence feature of the Pipeline to get location information from the client.
# This information is used to populate properties containing JavaScript snippets, which are then bundled together into a single JavaScript block by the 'JsonBundler' and 'JavaScriptBuilder' elements.
# This JavaScript is then used to obtain the additional evidence from the client and pass it back to the server.
# The Pipeline running on the server then processes this evidence to populate a new JSON result object that is returned to the client.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/location-python/blob/main/examples/cloud/web.py)

from fiftyone_location.location_pipelinebuilder import LocationPipelineBuilder
from fiftyone_pipeline_core.web import webevidence
import json

# First create the location pipeline with the desired settings.

# You need to create a resource key at https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=location-python&utm_content=examples-cloud-web.py&utm_term=top
# and paste it into the code, replacing !!YOUR_RESOURCE_KEY!! below.
# Alternatively, add a resource_key environment variable
import os
if "resource_key" in os.environ:
    resource_key = os.environ["resource_key"]
else:
    resource_key = "!!YOUR_RESOURCE_KEY!!"

if resource_key == "!!YOUR_RESOURCE_KEY!!":
    print("""
    You need to create a resource key at
    https://configure.51degrees.com?utm_source=code&utm_medium=example&utm_campaign=location-python&utm_content=examples-cloud-web.py&utm_term=resource-key-required and paste it into the code,
    'replacing !!YOUR_RESOURCE_KEY!!
    To get a resourcekey with the properties used in this example go to https://configure.51degrees.com/GCrtGh1L?utm_source=code&utm_medium=example&utm_campaign=location-python&utm_content=examples-cloud-web.py&utm_term=resource-key-required
    """)
else:

    # Here we add some callback settings for the page to make a request with extra evidence from the client side, in this case the Flask /json route we will make below

    javascript_builder_settings = {
        "endpoint": "/json"
    }

    pipeline = LocationPipelineBuilder(resource_key=resource_key, settings={"javascript_builder_settings": javascript_builder_settings}).build()

    from flask import Flask, request

    app = Flask(__name__)

    # First we make a JSON route that will be called from the client side and will return
    # a JSON encoded property database using any additional evidence provided by the client

    @app.route('/json', methods=['POST'])
    def jsonroute():

        # Create the flowData object for the JSON route
        flowData = pipeline.create_flowdata()

        # Add any information from the request (headers, cookies and additional
        # client side provided information)

        flowData.evidence.add_from_dict(webevidence(request))

        # Process the flowData
        flowData.process()

        # Return the JSON from the JSONBundler engine
        return json.dumps(flowData.jsonbundler.json)

    # Helper function to get a property value if it exists and return
    # the reason why if it doesn't
    def getValueHelper(flowdata, engine, propertyKey):

        engineProperties = getattr(flowdata, engine)

        propertyValue = getattr(engineProperties, propertyKey)

        if propertyValue.hasValue():
            return propertyValue.value()
        else:
            return propertyValue.no_value_message()

    # In the main route we dynamically update the screen's device property display
    # using the above JSON route

    @app.route('/')
    def server():

        # Create the flowData object for the JSON route
        flowData = pipeline.create_flowdata()

        # Add any information from the request (headers, cookies and additional
        # client side provided information)

        flowData.evidence.add_from_dict(webevidence(request))

        # Process the flowData

        flowData.process()

        # Generate the HTML
        output = ""

        # Add the JavaScript created by the pipeline
        output += "<script>"
        output += flowData.javascriptbuilder.javascript
        output += "</script>"


        output += "<h1>Client side evidence</h1>"

        # Print a button which gets the user's location information
        # This is then sent to the previously specified json endpoint
        # Data comes back from the request and populates the country in the HTML

        output += """

        <p>After you select the "use my location" button below, client side JavaScript will
        update the country field using this information.</p>

        <p>Country: <span id=country></span></p>

        <button type="button" onclick="getLocation()">Use my location</button>

        <script>

        let getLocation = function() {
            fod.complete(function (data) {
                document.getElementById("country").innerHTML = data.location.country
            }, 'location');
        }
            
        </script>


        """

        return output

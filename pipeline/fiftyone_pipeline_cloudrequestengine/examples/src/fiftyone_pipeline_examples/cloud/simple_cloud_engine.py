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

## @example cloud/simple_cloud_engine.py
#
# This example creates a cloud engine of its own and adds it to a pipeline.
# A cloud engine gets its results from a remote service rather than working
# them out itself. Here the service takes a date of birth and answers with
# the star sign.
#
# It is the simple flow element example in fiftyone_pipeline_core with the
# work moved to a remote service. The 51Degrees cloud engines, such as
# device detection, work the same way with the 51Degrees cloud service.
#
# You will learn:
#
# 1. How to write a cloud engine, which reads its part of the answer that a
#    cloud request engine gets from the service
# 2. How to add a cloud request engine and a cloud engine to a pipeline
# 3. How to read a property the service gives no value for, with the reason
#
# A cloud request engine makes three kinds of request. When the pipeline is
# built, it asks the service which properties the resource key gives, and
# which evidence the service reads. Then for each flow data it sends the
# evidence and gets the results back, with a section for each product. A
# cloud engine reads the section named by its data key.
#
# So that the example runs anywhere, with no key and no network, it starts
# a small star sign service of its own on this machine. The service answers
# those three requests in the shapes the 51Degrees cloud service uses. To use
# a real service, give its address to the cloud request engine instead.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/pipeline/fiftyone_pipeline_cloudrequestengine/examples/src/fiftyone_pipeline_examples/cloud/simple_cloud_engine.py).
#
# Run it from the examples folder, once the requirements there are
# installed, with
# ```
# python -m fiftyone_pipeline_examples.cloud.simple_cloud_engine
# ```
#
# Expected output, before the Find out more section:
# ```
# With a date of birth of 1992-12-18, your star sign is Sagittarius.
# With a date of birth of 1990-12-25, your star sign is Capricorn.
# With a date of birth of 1992-04-15, your star sign is Aries.
# With no date of birth, there is no star sign. The service needs a date of birth in the form YYYY-MM-DD to find a star sign.
# ```

import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from fiftyone_pipeline_cloudrequestengine.cloudengine import CloudEngine
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import (
    CloudRequestEngine)
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Pipeline API documentation",
     "https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-simple_cloud_engine.py&utm_term=find-out-more-documentation"),
    ("The 51Degrees cloud service",
     "https://51degrees.com/documentation/_services__cloud__index.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-simple_cloud_engine.py&utm_term=find-out-more-cloud-service"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-simple_cloud_engine.py&utm_term=find-out-more-resource-keys"),
    ("Contact us",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-examples-src-fiftyone_pipeline_examples-cloud-simple_cloud_engine.py&utm_term=find-out-more-contact"),
    ("Pipeline API for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"),
    ("Device detection for Python, with cloud engines like this one",
     "https://github.com/51Degrees/51degrees-python/tree/main/device-detection"),
    ("Pipeline API specification",
     "https://github.com/51Degrees/specifications/tree/main/pipeline-specification"),
]

# The evidence the service reads, a date of birth in the form YYYY-MM-DD, as
# a date input in a web form sends it in the query string.
DATE_OF_BIRTH = "query.dateOfBirth"

# The dates of birth the example looks up. None sends no date of birth, to
# show a property the service gives no value for.
DATES_OF_BIRTH = ["1992-12-18", "1990-12-25", "1992-04-15", None]

# The resource key sent to the star sign service, which accepts any key.
RESOURCE_KEY = "star-sign-example"


class SimpleCloudEngine(CloudEngine):

    """!
    Star sign results, read from the "astrology" section of the service's
    answer and available as flowdata.astrology.

    CloudEngine does the work. When the pipeline is built, it takes its
    properties from the ones the service lists under the data key. For each
    flow data, it reads the section of the same name from the answer the
    cloud request engine got, and keeps each value as an
    AspectPropertyValue, which holds the value or the reason the service
    gave for having none.
    """

    def __init__(self):

        super(SimpleCloudEngine, self).__init__()

        self.datakey = "astrology"


def look_up(pipeline, date_of_birth):

    """!
    Process one date of birth, or none, and print the star sign or the
    reason the service gave for having none.
    """

    # Flow data carries the evidence into the pipeline and the results out
    # of it.
    flowdata = pipeline.create_flowdata()
    if date_of_birth is None:
        described = "no date of birth"
    else:
        flowdata.evidence.add(DATE_OF_BIRTH, date_of_birth)
        described = f"a date of birth of {date_of_birth}"

    # The cloud request engine sends the evidence to the service, and the
    # cloud engine reads its section of the answer.
    flowdata.process()

    star_sign = flowdata.astrology.starsign
    if star_sign.has_value():
        print(f"With {described}, your star sign is {star_sign.value()}.")
    else:
        print(f"With {described}, there is no star sign. "
              f"{star_sign.no_value_message()}")


def print_find_out_more():

    """!
    Print the "Find out more" section, a line of "=" and then each label
    with its link.
    """

    print("=" * 79)
    print("Find out more:")
    for label, url in FIND_OUT_MORE:
        print(f"\t{label}: {url}")


def main():

    server, endpoint = start_star_sign_service()
    try:
        # The cloud request engine makes the requests to the service. The
        # endpoint is given here because the star sign service is not the
        # 51Degrees cloud service. A pipeline for a 51Degrees product
        # leaves it out, and the cloud request engine then reads it from
        # the _51DEGREES_CLOUD_ENDPOINT environment variable, or uses
        # cloud.51degrees.com.
        cloud_request_engine = CloudRequestEngine({
            "resource_key": RESOURCE_KEY,
            "cloud_endpoint": endpoint,
        })

        # A console has no page, so leave out the elements that write the
        # client-side script and set response headers.
        settings = {
            "add_javascript_builder": False,
            "use_setheader_properties": False,
        }

        # A cloud engine goes after the cloud request engine whose answer
        # it reads. Building the pipeline asks the service for its
        # properties.
        pipeline = PipelineBuilder(settings) \
            .add(cloud_request_engine) \
            .add(SimpleCloudEngine()) \
            .build()

        # Closing the pipeline closes the engines in it.
        with pipeline:
            for date_of_birth in DATES_OF_BIRTH:
                look_up(pipeline, date_of_birth)

    finally:
        server.shutdown()
        server.server_close()

    print_find_out_more()


# The star sign service, which stands in for a remote service so that the
# example runs with no key and no network. A real service runs on another
# machine, and the example needs nothing below this line to use one.

# Each star sign, with the month and day it starts and the month and day it
# ends. Capricorn runs over the end of the year.
STAR_SIGNS = [
    ("Aries", (3, 21), (4, 19)),
    ("Taurus", (4, 20), (5, 20)),
    ("Gemini", (5, 21), (6, 20)),
    ("Cancer", (6, 21), (7, 22)),
    ("Leo", (7, 23), (8, 22)),
    ("Virgo", (8, 23), (9, 22)),
    ("Libra", (9, 23), (10, 22)),
    ("Scorpio", (10, 23), (11, 21)),
    ("Sagittarius", (11, 22), (12, 21)),
    ("Capricorn", (12, 22), (1, 19)),
    ("Aquarius", (1, 20), (2, 18)),
    ("Pisces", (2, 19), (3, 20)),
]

# The products the service offers for a resource key, each with its
# properties. A cloud engine's data key names its product.
ACCESSIBLE_PROPERTIES = {
    "Products": {
        "astrology": {
            "DataTier": "Free",
            "Properties": [{
                "Name": "StarSign",
                "Type": "String",
                "Category": "Astrology",
                "Description": "The star sign for the date of birth.",
            }],
        },
    },
}

# The evidence the service reads.
EVIDENCE_KEYS = [DATE_OF_BIRTH]

# The reason the service gives in place of a star sign when it has none.
NO_STAR_SIGN = ("The service needs a date of birth in the form YYYY-MM-DD "
                "to find a star sign.")


def find_star_sign(month, day):

    """!
    The star sign for a month and day, from the table above.
    """

    birthday = (month, day)
    for name, start, end in STAR_SIGNS:
        if start <= end:
            if start <= birthday <= end:
                return name
        # A star sign that runs over the end of the year.
        elif birthday >= start or birthday <= end:
            return name
    return None


def astrology_section(date_of_birth):

    """!
    The astrology section of an answer. A property with no value is null,
    with the reason under its name followed by "nullreason", as the
    51Degrees cloud service gives it.
    """

    try:
        born = date.fromisoformat(date_of_birth)
    except (TypeError, ValueError):
        return {"starsign": None, "starsignnullreason": NO_STAR_SIGN}
    return {"starsign": find_star_sign(born.month, born.day)}


class StarSignRequestHandler(BaseHTTPRequestHandler):

    """!
    Answers the requests a cloud request engine makes, at the paths it
    makes them to.
    """

    def do_GET(self):

        path = urlsplit(self.path).path.lower()
        if path.endswith("/accessibleproperties"):
            self.send_json(ACCESSIBLE_PROPERTIES)
        elif path.endswith("/evidencekeys"):
            self.send_json(EVIDENCE_KEYS)
        else:
            self.send_error(404)

    def do_POST(self):

        # The results for one flow data, posted to <resource key>.json. The
        # evidence arrives as a form, each field named by an evidence key
        # without its prefix, so query.dateOfBirth arrives as dateOfBirth.
        if not urlsplit(self.path).path.lower().endswith(".json"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        # Evidence keys ignore letter case, so field names do as well.
        fields = {name.lower(): values[0] for name, values in form.items()}
        self.send_json(
            {"astrology": astrology_section(fields.get("dateofbirth"))})

    def send_json(self, value):

        body = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):

        # Leave the console to the example's own output.
        pass


def start_star_sign_service():

    """!
    Start the star sign service on this machine and return the server and
    the endpoint to give a cloud request engine. Port 0 lets the operating
    system choose a free port.
    """

    server = ThreadingHTTPServer(("127.0.0.1", 0), StarSignRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/api/"


if __name__ == "__main__":
    main()

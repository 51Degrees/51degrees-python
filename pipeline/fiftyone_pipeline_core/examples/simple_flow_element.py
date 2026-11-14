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


## @example simple_flow_element.py
#
# This example creates a flow element of its own and adds it to a pipeline.
# The element takes a date of birth as evidence and works out the star sign
# from a table held in its code.
#
# You will learn:
#
# 1. How to write a flow element, which names the evidence it reads and the
#    properties it gives, and works out their values
# 2. How to add the flow element to a pipeline
# 3. How to pass evidence to the pipeline and read the results
#
# The other star sign examples build on this one. The on-premise engine
# example in fiftyone_pipeline_engines reads the table from a data file, the
# client-side evidence example beside this one gets the date of birth from a
# form in a web page, and the cloud engine example in the cloud request
# engine's examples gets the star sign from a remote service.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/pipeline/fiftyone_pipeline_core/examples/simple_flow_element.py).
#
# It needs no data file, no key and no network. Run it from the pipeline
# folder, once fiftyone_pipeline_core is installed, with
# ```
# python fiftyone_pipeline_core/examples/simple_flow_element.py
# ```
#
# Expected output, before the Find out more section:
# ```
# With a date of birth of 1992-12-18, your star sign is Sagittarius.
# With a date of birth of 1990-12-25, your star sign is Capricorn.
# With a date of birth of 1992-04-15, your star sign is Aries.
# ```

from datetime import date

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Pipeline API examples",
     "https://51degrees.com/documentation/_pipeline_api__examples__index.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core-examples-simple_flow_element.py&utm_term=find-out-more-examples"),
    ("Pipeline API documentation",
     "https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core-examples-simple_flow_element.py&utm_term=find-out-more-documentation"),
    ("Build your own",
     "https://51degrees.com/build-your-own?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core-examples-simple_flow_element.py&utm_term=find-out-more-build-your-own"),
    ("Contact us",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core-examples-simple_flow_element.py&utm_term=find-out-more-contact"),
    ("Pipeline API for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"),
    ("Pipeline API specification",
     "https://github.com/51Degrees/specifications/tree/main/pipeline-specification"),
]

# The evidence the flow element reads, a date of birth in the form
# YYYY-MM-DD, as a date input in a web form sends it in the query string.
DATE_OF_BIRTH = "query.dateOfBirth"

# The dates of birth the example looks up.
DATES_OF_BIRTH = ["1992-12-18", "1990-12-25", "1992-04-15"]

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


class SimpleFlowElement(FlowElement):

    """!
    A flow element that takes a date of birth as evidence and gives the star
    sign, worked out from the table held in this example.
    """

    def __init__(self):

        super(SimpleFlowElement, self).__init__()

        # The results are kept in the flow data under this key, so they are
        # read as flowdata.astrology.
        self.datakey = "astrology"

        # The properties the flow element gives, each named in lower case,
        # as the 51Degrees flow elements name theirs.
        self.properties = {
            "starsign": {
                "type": "string",
                "description": "The star sign for the date of birth."
            }
        }

    def get_evidence_key_filter(self):

        """!
        The evidence the flow element reads. The pipeline sets aside any
        evidence that no flow element reads.
        """

        return BasicListEvidenceKeyFilter([DATE_OF_BIRTH])

    def process_internal(self, flowdata):

        """!
        The work of the flow element, which reads the evidence and adds the
        results to the flow data.
        """

        result = {}

        date_of_birth = flowdata.evidence.get(DATE_OF_BIRTH)
        if date_of_birth:
            born = date.fromisoformat(date_of_birth)
            result["starsign"] = find_star_sign(born.month, born.day)

        # The results go into element data, which the flow data keeps under
        # the flow element's data key.
        flowdata.set_element_data(ElementDataDictionary(self, result))


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

    # A console has no page, so leave out the elements that write the
    # client-side script and set response headers.
    settings = {
        "add_javascript_builder": False,
        "use_setheader_properties": False,
    }

    pipeline = PipelineBuilder(settings).add(SimpleFlowElement()).build()

    # Closing the pipeline closes the flow elements in it.
    with pipeline:

        for date_of_birth in DATES_OF_BIRTH:

            # Flow data carries the evidence into the pipeline and the
            # results out of it.
            flowdata = pipeline.create_flowdata()
            flowdata.evidence.add(DATE_OF_BIRTH, date_of_birth)
            flowdata.process()

            print(
                f"With a date of birth of {date_of_birth}, your star sign "
                f"is {flowdata.astrology.starsign}.")

    print_find_out_more()


if __name__ == "__main__":
    main()

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


## @example simple_onpremise_engine.py
#
# This example creates an on-premise engine of its own and adds it to a
# pipeline. The engine takes a date of birth as evidence and works out the
# star sign from a table it reads from a data file, starsigns.csv, beside
# this example.
#
# It is the simple flow element example in fiftyone_pipeline_core with the
# table moved out of the code and into a data file. An engine is a flow
# element with more features, one of which is a data file that the
# pipeline's data file update service looks after. The 51Degrees on-premise
# engines, such as device detection, work the same way with much larger
# data files.
#
# You will learn:
#
# 1. How to write an engine that reads its data from a data file
# 2. How to register the data file, so the pipeline can look after it
# 3. How to pass evidence to the pipeline and read the results
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/pipeline/fiftyone_pipeline_engines/examples/simple_onpremise_engine.py).
#
# It needs no key and no network, and its data file is in this repository.
# Run it from the pipeline folder, once fiftyone_pipeline_core and
# fiftyone_pipeline_engines are installed, with
# ```
# python fiftyone_pipeline_engines/examples/simple_onpremise_engine.py
# ```
# To read the star signs from another file, give its path as the first
# argument.
#
# Expected output, before the Find out more section:
# ```
# With a date of birth of 1992-12-18, your star sign is Sagittarius.
# With a date of birth of 1990-12-25, your star sign is Capricorn.
# With a date of birth of 1992-04-15, your star sign is Aries.
# ```

import csv
import os
import sys
from datetime import date

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines.aspectdata_dictionary import \
    AspectDataDictionary
from fiftyone_pipeline_engines.datafile import DataFile
from fiftyone_pipeline_engines.engine import Engine

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Pipeline API documentation",
     "https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-examples-simple_onpremise_engine.py&utm_term=find-out-more-documentation"),
    ("Data file updates",
     "https://51degrees.com/documentation/_pipeline_api__features__automatic_datafile_updates.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-examples-simple_onpremise_engine.py&utm_term=find-out-more-data-file-updates"),
    ("Build your own",
     "https://51degrees.com/build-your-own?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-examples-simple_onpremise_engine.py&utm_term=find-out-more-build-your-own"),
    ("Contact us",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_engines-examples-simple_onpremise_engine.py&utm_term=find-out-more-contact"),
    ("Pipeline API for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"),
    ("Device detection for Python, an on-premise engine with a data file",
     "https://github.com/51Degrees/51degrees-python/tree/main/device-detection"),
    ("Pipeline API specification",
     "https://github.com/51Degrees/specifications/tree/main/pipeline-specification"),
]

# The data file the example reads when it is given none, which is the one
# beside this example.
DATA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "starsigns.csv")

# The evidence the engine reads, a date of birth in the form YYYY-MM-DD, as
# a date input in a web form sends it in the query string.
DATE_OF_BIRTH = "query.dateOfBirth"

# The dates of birth the example looks up.
DATES_OF_BIRTH = ["1992-12-18", "1990-12-25", "1992-04-15"]


def month_and_day(text):

    """!
    A month and day written as MM-DD in the data file, as a pair of
    numbers that sort in date order.
    """

    month, day = text.split("-")
    return (int(month), int(day))


class SimpleOnPremiseEngine(Engine):

    """!
    An engine that takes a date of birth as evidence and gives the star
    sign, worked out from a table it reads from a data file.
    """

    def __init__(self, data_file_path):

        super(SimpleOnPremiseEngine, self).__init__()

        # The results are kept in the flow data under this key, so they are
        # read as flowdata.astrology.
        self.datakey = "astrology"

        # The properties the engine gives, each named in lower case. Aspect
        # data, the element data of an engine, keeps its values under names
        # in lower case and finds a value by the name exactly as asked.
        self.properties = {
            "starsign": {
                "type": "string",
                "description": "The star sign for the date of birth."
            }
        }

        # Register the data file. When the engine is added to a pipeline,
        # the pipeline's data file update service looks after the file. A
        # 51Degrees data file can be downloaded again when a new one is
        # published, and checked for changes on disk. This file is never
        # published, so both are turned off.
        self.register_data_file(DataFile(
            flow_element=self,
            identifier="starsigns",
            path=data_file_path,
            auto_update=False,
            file_system_watcher=False))

        # Read the table for the first time.
        self.refresh(self.data_file.identifier)

    def refresh(self, identifier):

        """!
        Read the table from the data file into memory, in place of any
        table read before. An engine loads its data here, so this runs when
        the engine is made and whenever its data file is refreshed.
        """

        star_signs = []
        with open(self.data_file.path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                star_signs.append((
                    row["name"],
                    month_and_day(row["start"]),
                    month_and_day(row["end"])))
        self.star_signs = star_signs

    def find_star_sign(self, month, day):

        """!
        The star sign for a month and day, from the table read from the
        data file.
        """

        birthday = (month, day)
        for name, start, end in self.star_signs:
            if start <= end:
                if start <= birthday <= end:
                    return name
            # A star sign that runs over the end of the year.
            elif birthday >= start or birthday <= end:
                return name
        return None

    def get_evidence_key_filter(self):

        """!
        The evidence the engine reads. The pipeline sets aside any evidence
        that no flow element reads.
        """

        return BasicListEvidenceKeyFilter([DATE_OF_BIRTH])

    def process_internal(self, flowdata):

        """!
        The work of the engine, which reads the evidence and adds the
        results to the flow data.
        """

        result = {}

        date_of_birth = flowdata.evidence.get(DATE_OF_BIRTH)
        if date_of_birth:
            born = date.fromisoformat(date_of_birth)
            result["starsign"] = self.find_star_sign(born.month, born.day)

        # Aspect data is the element data of an engine. When asked for a
        # property it holds no value for, it asks the engine's missing
        # property service why.
        flowdata.set_element_data(AspectDataDictionary(self, result))


def print_find_out_more():

    """!
    Print the "Find out more" section, a line of "=" and then each label
    with its link.
    """

    print("=" * 79)
    print("Find out more:")
    for label, url in FIND_OUT_MORE:
        print(f"\t{label}: {url}")


def main(argv):

    # The data file is the first argument, or the one beside this example.
    data_file_path = argv[0] if len(argv) > 0 else DATA_FILE

    # A console has no page, so leave out the elements that write the
    # client-side script and set response headers.
    settings = {
        "add_javascript_builder": False,
        "use_setheader_properties": False,
    }

    engine = SimpleOnPremiseEngine(data_file_path)
    pipeline = PipelineBuilder(settings).add(engine).build()

    # Closing the pipeline closes the engine, which stops the data file
    # update service looking after its data file.
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
    main(sys.argv[1:])

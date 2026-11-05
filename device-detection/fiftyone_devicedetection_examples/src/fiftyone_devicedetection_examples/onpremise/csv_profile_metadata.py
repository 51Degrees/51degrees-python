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

## @example onpremise/csv_profile_metadata.py
# @brief CSV Profile Metadata Example - On-premise
#
# This example demonstrates how to read hardware profile data from the
# 51Degrees HardwarePlatform CSV export file and output selected properties
# as JSON. The CSV file (51Degrees-Tac-HardwarePlatform.csv) contains one
# row per hardware profile with all properties pre-extracted, making it
# much faster than iterating profiles via the SWIG metadata API.
#
# Multi-value properties (TAC, HardwareName, etc.) are pipe-delimited
# in the CSV and are split into JSON arrays in the output.
#
# Required PyPi Dependencies:
# - fiftyone_devicedetection_examples (for ExampleUtils)

import csv
import json
import sys

from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger

# CSV file name to search for
CSV_FILE_NAME = "51Degrees-Tac-HardwarePlatform.csv"

# Target columns to extract (CSV header names)
TARGET_COLUMNS = ["ProfileId", "HardwareVendor", "HardwareModel", "HardwareName",
                  "NativeModel", "NativeName", "TAC"]

# Columns whose values are pipe-delimited lists
MULTI_VALUE_COLUMNS = ["TAC", "HardwareName", "NativeName", "NativeModel"]

# Where to ask for a copy of the hardware profile export, tagged with this
# example.
CONTACT_US = "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-csv_profile_metadata.py&utm_term=enterprise-data-file"


def flush_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def stderr_print(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr, flush=True)


def run(csv_file, output_file, output, limit=None):
    output(f"Reading CSV file: {csv_file}")

    out_stream = open(output_file, 'w') if output_file else sys.stdout

    try:
        out_stream.write("[\n")

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0

            for row in reader:
                if limit and count >= limit:
                    break

                record = {}
                for col in TARGET_COLUMNS:
                    value = row.get(col, "")
                    if col in MULTI_VALUE_COLUMNS:
                        record[col.lower()] = value.split("|") if value else []
                    else:
                        record[col.lower()] = value

                if count > 0:
                    out_stream.write(",\n")
                out_stream.write(json.dumps(record, indent=2))
                out_stream.flush()

                count += 1
                if count % 10000 == 0:
                    output(f"  Processed {count} profiles...")

        out_stream.write("\n]\n")

        output(f"Extracted {count} hardware profiles")
        if output_file:
            output(f"Results written to: {output_file}")
    finally:
        if output_file and out_stream:
            out_stream.close()


def main(argv):
    csv_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(CSV_FILE_NAME)
    output_arg = argv[1] if len(argv) > 1 else "-"
    output_file = None if output_arg == "-" else output_arg
    limit = int(argv[2]) if len(argv) > 2 else None

    logger = Logger(min_level="info")
    output_func = flush_print if output_file else stderr_print

    if csv_file is not None:
        run(csv_file, output_file, output_func, limit)
    else:
        # The export is not one of the free data files, so the example says
        # what it needs and where to ask for it, and stops.
        print(f"Listing the hardware profiles needs the {CSV_FILE_NAME} "
              "export, which is not one of the free data files. Give its "
              "path as the first command line argument, or contact us for a "
              f"copy at {CONTACT_US}")


if __name__ == "__main__":
    main(sys.argv[1:])

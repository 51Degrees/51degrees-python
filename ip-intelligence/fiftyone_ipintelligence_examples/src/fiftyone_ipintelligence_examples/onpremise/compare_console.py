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

## @example onpremise/compare_console.py
# @brief Compare Console Example - On-premise
#
# This example takes a CSV file containing 'known and true' IP-location
# records (IP addresses with associated latitudes and longitudes) and
# compares them against the location returned by the on-premise IP
# intelligence engine. This is useful for understanding how the results of
# an IP-to-location service compare to real world information, especially
# when evaluating different solutions.
#
# The input CSV (geoip_comparison_evidence.csv in the data repository's
# ip-intelligence folder) provides these fields:
#   DateTimeUtc, Latitude, Longitude, Ip, AddressFamily, Continent, Country
#
# For each record the engine is used to obtain the latitude and longitude
# for the IP address. The great-circle distance in kilometres between the
# true location and the returned location is then calculated, along with the
# location confidence and whether an area was returned.
#
# This example requires an enterprise IP intelligence data file (.ipi). To
# obtain an enterprise data file for testing, please contact us:
# https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-compare_console.py&utm_term=top
#
# Required PyPi Dependencies:
# - fiftyone_ipintelligence

import argparse
import csv
import math
import sys

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger
from fiftyone_ipintelligence_shared.example_constants import ENTERPRISE_DATAFILE_NAME

# Name of the truth CSV file in the data repository.
GEOIP_COMPARISON_EVIDENCE_FILE_NAME = "geoip_comparison_evidence.csv"

# Mean radius of the earth in kilometres, used for the distance calculation.
EARTH_RADIUS_KM = 6371.0

# Default number of records to process. The full file contains 50,000
# records; a smaller default keeps the example quick to run.
RECORD_LIMIT = 1000

OUTPUT_FIELDS = [
    "DateTimeUtc", "Ip", "AddressFamily",
    "TruthLatitude", "TruthLongitude", "TruthCountry",
    "ResultLatitude", "ResultLongitude", "ResultCountry",
    "Confidence", "Found", "DistanceKms"]


def haversine_km(lat1, lon1, lat2, lon2):
    """!
    Great-circle distance in kilometres between two latitude/longitude
    points.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class CompareConsole():
    def run(self, data_file, truth_file, logger, output, record_limit=RECORD_LIMIT):

        pipeline = IpIntelligencePipelineBuilder(
            data_file_path = data_file,
            performance_profile = "LowMemory",
            usage_sharing = False,
            auto_update = False,
            licence_keys = "").add_logger(logger).build()

        ExampleUtils.check_data_file(pipeline, logger)

        writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()

        processed = 0
        found = 0
        with open(truth_file, "r", newline="", encoding="utf-8") as fin:
            for truth in csv.DictReader(fin):
                if processed >= record_limit:
                    break
                processed += 1
                result = self.compare(pipeline, truth)
                if result["Found"]:
                    found += 1
                writer.writerow(result)

        logger.log("info",
            f"Compared {processed} records; {found} resolved to a location")

    def compare(self, pipeline, truth):

        data = pipeline.create_flowdata()
        data.evidence.add_from_dict({"query.client-ip": truth["Ip"]})
        data.process()
        ip_data = data.ip

        row = {
            "DateTimeUtc": truth.get("DateTimeUtc", ""),
            "Ip": truth.get("Ip", ""),
            "AddressFamily": truth.get("AddressFamily", ""),
            "TruthLatitude": truth.get("Latitude", ""),
            "TruthLongitude": truth.get("Longitude", ""),
            "TruthCountry": truth.get("Country", ""),
            "ResultLatitude": "",
            "ResultLongitude": "",
            "ResultCountry": ExampleUtils.get_human_readable(ip_data, "country"),
            "Confidence": ExampleUtils.get_human_readable(ip_data, "locationconfidence"),
            "Found": False,
            "DistanceKms": "",
        }

        latitude = ExampleUtils.get_value(ip_data, "latitude")
        longitude = ExampleUtils.get_value(ip_data, "longitude")
        if latitude is not None and latitude.has_value() and \
                longitude is not None and longitude.has_value():
            row["ResultLatitude"] = latitude.value()
            row["ResultLongitude"] = longitude.value()
            row["Found"] = True
            try:
                row["DistanceKms"] = round(haversine_km(
                    float(truth["Latitude"]), float(truth["Longitude"]),
                    float(latitude.value()), float(longitude.value())), 3)
            except (ValueError, TypeError):
                # The truth record did not provide a usable latitude or
                # longitude, so the distance cannot be calculated.
                row["DistanceKms"] = ""

        return row


def main(argv):
    ap = argparse.ArgumentParser(
        description="Compare IP intelligence results against known truth data.")
    ap.add_argument("-d", "--data_file", default=None,
        help="Path to the IP intelligence data file")
    ap.add_argument("-t", "--truth_file", default=None,
        help="Path to the truth CSV file")
    ap.add_argument("-o", "--output_file", default="compare-output.csv",
        help="Path to write the comparison CSV to")
    ap.add_argument("-n", "--record_limit", type=int, default=RECORD_LIMIT,
        help="Maximum number of truth records to process")
    args = ap.parse_args(argv)

    data_file = args.data_file or ExampleUtils.find_file(ENTERPRISE_DATAFILE_NAME)
    truth_file = args.truth_file or ExampleUtils.find_file(
        GEOIP_COMPARISON_EVIDENCE_FILE_NAME)

    logger = Logger(min_level="info")

    if data_file and truth_file:
        with open(args.output_file, "w", newline="", encoding="utf-8") as fout:
            CompareConsole().run(
                data_file, truth_file, logger, fout, args.record_limit)
        logger.log("info", f"Comparison complete. See results in: '{args.output_file}'")
    else:
        logger.log("error",
            "Failed to find a data file or truth file. Make sure the "
            "data submodule is there, by running "
            "`git submodule update --init --recursive`. To obtain an enterprise "
            "data file for testing, please contact us: "
            "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-compare_console.py&utm_term=data-file-required")

if __name__ == "__main__":
    main(sys.argv[1:])

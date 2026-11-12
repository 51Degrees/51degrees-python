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
# @brief Getting Started Web Example - On-premise
#
# A simple Flask web application that resolves the IP address of the
# visitor (or an IP supplied as the "client-ip" query parameter) using
# the on-premise IP intelligence engine, and renders a dropdown of
# countries ordered with the most probable country first.
#
# The country names are localized using the visitor's Accept-Language
# header. Append "&translation=fr_FR" to the url to force a language.
#
# Run with:
# ```
# python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_web
# ```

from flask import Flask, request

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder
from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_examples.onpremise.countries_pipeline import (
    add_country_translation, build_country_options)
from fiftyone_ipintelligence_shared.example_constants import LITE_DATAFILE_NAME

# Where to ask for a copy of the Enterprise data file, tagged with this
# example.
CONTACT_US = "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-src-fiftyone_ipintelligence_examples-onpremise-gettingstarted_web-app.py&utm_term=enterprise-data-file"

app = Flask(__name__)

pipeline = None


def build_pipeline(data_file):
    global pipeline
    builder = IpIntelligencePipelineBuilder(
        data_file_path = data_file,
        performance_profile = "LowMemory",
        usage_sharing = False,
        auto_update = False,
        licence_keys = "")
    # Add the country code and countries translation engines on top of the
    # on-premise IP Intelligence engine.
    add_country_translation(builder)
    pipeline = builder.build()
    return pipeline


def get_value(ip_data, property):
    return ExampleUtils.get_human_readable(ip_data, property)


def country_dropdown(translated):
    # Only the Enterprise data file has the country codes the dropdown is
    # built from.
    if not ExampleUtils.has_property(
            pipeline.flow_elements_list["ip"], "CountryCodesGeographical"):
        return (f"<p>The country dropdown {ExampleUtils.NEEDS_ENTERPRISE}. "
                f"<a href=\"{CONTACT_US}\">Contact us</a> for a copy.</p>")

    # The geographical "All" lists are index-aligned: option i is
    # (CountryCodesGeographicalAll[i], CountryNamesGeographicalAllTranslated[i]),
    # most probable country first.
    codes = translated.get("CountryCodesGeographicalAll")
    names = translated.get("CountryNamesGeographicalAllTranslated")
    if not codes.has_value() or not names.has_value():
        return "<p>No country information available in this data file.</p>"
    options = build_country_options(codes.value(), names.value())
    return f"""
    <select id="CountryNamesGeographicalAllTranslated"
            name="CountryNamesGeographicalAllTranslated">
{options}
    </select>"""


@app.route("/")
def index():

    # Create the flowdata object for this request. It is closed when the
    # route returns, once the page has been built from it, which releases
    # the results of the lookup straight away.
    with pipeline.create_flowdata() as flowdata:

        # Use the IP address supplied as a query parameter, or fall back
        # to the address of the requester.
        client_ip = request.args.get("client-ip", request.remote_addr)
        flowdata.evidence.add("query.client-ip", client_ip)

        # Supply the browser language so the country names are localized. The
        # Accept-Language header is used by default, overridable with a
        # "translation" query parameter.
        accept_language = request.headers.get("Accept-Language")
        if accept_language:
            flowdata.evidence.add("header.accept-language", accept_language)
        translation = request.args.get("translation")
        if translation:
            flowdata.evidence.add("query.translation", translation)

        # Process the flowdata
        flowdata.process()

        ip_data = flowdata.ip
        translated = flowdata.get("countrynamestranslated")

        return f"""
        <h2>51Degrees IP Intelligence - Getting Started Web (On-Premise)</h2>
        <p>IP address: {client_ip}</p>
        <ul>
            <li>Registered Name: {get_value(ip_data, "registeredname")}</li>
            <li>Registered Owner: {get_value(ip_data, "registeredowner")}</li>
            <li>Registered Country: {get_value(ip_data, "registeredcountry")}</li>
        </ul>
        <h3>Country</h3>
        <p>Most probable country first, then every other country alphabetically.</p>
        {country_dropdown(translated)}
        <p>Add ?client-ip=x.x.x.x to the url to lookup a different address, and
        &amp;translation=fr_FR to choose a language.</p>
        """


def main(data_file = None):
    if not data_file:
        data_file = ExampleUtils.find_file(LITE_DATAFILE_NAME)
    if not data_file:
        raise Exception(
            "Failed to find an IP intelligence data file. Make sure the "
            "data submodule is there, by running "
            "`git submodule update --init --recursive`, and run this "
            "example again to download the file, or supply the path to a "
            "data file as the first command line argument.")
    # The pipeline lives as long as the app, and is closed when the server
    # stops, which releases the native data it holds.
    with build_pipeline(data_file):
        app.run(debug=False)


if __name__ == "__main__":
    main()

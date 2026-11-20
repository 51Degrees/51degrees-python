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


## @example cloud/gettingstarted.py
# 
# @include{doc} example-require-resourcekey.txt
# 
# Expected output, before the Find out more section:
# ```
# What country is at coordinates:-0.9822207999999999, 51.458048?
# United Kingdom
# 
# ```

from fiftyone_location.location_pipelinebuilder import LocationPipelineBuilder

# First create the device detection pipeline with the desired settings.

# You need to create a resource key at https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=top
# and paste it into the code, replacing !!YOUR_RESOURCE_KEY!! below.
# Alternatively, add a _51DEGREES_RESOURCE_KEY environment variable.
import os

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Geolocation",
     "https://51degrees.com/geolocation?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=find-out-more-geolocation"),
    ("Resource keys",
     "https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=find-out-more-resource-keys"),
    ("Pricing",
     "https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=find-out-more-pricing"),
    ("Location for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/location"),
]


resource_key = os.environ.get("_51DEGREES_RESOURCE_KEY")
if not resource_key:
    resource_key = "!!YOUR_RESOURCE_KEY!!"

if resource_key == "!!YOUR_RESOURCE_KEY!!":
    print("""
    You need to create a resource key at
    https://51degrees.com/configure?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=resource-key-required and set the
    _51DEGREES_RESOURCE_KEY environment variable to it, or paste it into the
    code in place of !!YOUR_RESOURCE_KEY!!.
    To get a resource key with the properties used in this example go to https://51degrees.com/configure/GCrtGh1L?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=examples-cloud-gettingstarted.py&utm_term=resource-key-required
    """)
else:

    pipeline = LocationPipelineBuilder(resource_key=resource_key).build()

    # We create a FlowData object from the pipeline
    # this is used to add evidence to and then process

    flow_data = pipeline.create_flowdata()

    # Here we add a longitude and latitude as evidence

    latitude = "51.458048"
    longitude = "-0.9822207999999999"

    flow_data.evidence.add("query.51D_Pos_latitude", latitude)
    flow_data.evidence.add("query.51D_Pos_longitude", longitude)

    # Now we process the FlowData

    flow_data.process()

    print("What country is at coordinates:" + longitude + ", " + latitude + "?")
    if flow_data.location.country.has_value():
        print(flow_data.location.country.value())
    else:
        print(flow_data.location.country.no_value_message())

print("=" * 79)
print("Find out more:")
for label, url in FIND_OUT_MORE:
    print(f"\t{label}: {url}")

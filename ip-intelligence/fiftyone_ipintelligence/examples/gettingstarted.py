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

from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder

# First create the IP intelligence pipeline with the desired settings.

data_file = "../../cxx/data/ip-intelligence/51Degrees-LiteV41.ipi"
resource_key = "!!YOUR_RESOURCE_KEY!!"

# Uncommment the line below 'On-Premise' and comment the line below 'Cloud' to
# switch to an On-Premise installation
# On-Premise
pipeline = IpIntelligencePipelineBuilder(data_file_path = data_file, licence_keys = "", performance_profile = 'LowMemory', auto_update=False, usage_sharing=False).build()

# Cloud
#pipeline = IpIntelligencePipelineBuilder(resource_key = resource_key).build()

# The pipeline is closed at the end of the with block, which releases the
# native data it holds.
with pipeline:
    # We create a FlowData object from the pipeline
    # this is used to add evidence to and then process. It is closed at the
    # end of its with block, which releases the results of the lookup.
    with pipeline.create_flowdata() as flowdata1:

        # Here we add an IPv4 address as evidence

        ipv4_address = "185.28.167.78"

        flowdata1.evidence.add("query.client-ip", ipv4_address)

        # Now we process the FlowData

        flowdata1.process()

        # To find the name the IP range is registered under we look at the
        # registeredname property inside the IP Intelligence Engine

        # first we check if this has a meaningful result

        print("What is IP address " + ipv4_address + " registered as? ")
        if flowdata1.ip.registeredname.has_value():
            print(flowdata1.ip.registeredname.value())
        else:
            # Output why the value isn't meaningful
            print(flowdata1.ip.registeredname.no_value_message())

    # Now we do the same with a new IP address, this time an IPv6 one

    with pipeline.create_flowdata() as flowdata2:

        ipv6_address = "2001:4860:4860::8888"

        flowdata2.evidence.add("query.client-ip", ipv6_address)

        flowdata2.process()

        print("What is IP address " + ipv6_address + " registered as? ")
        if flowdata2.ip.registeredname.has_value():
            print(flowdata2.ip.registeredname.value())
        else:
            print(flowdata2.ip.registeredname.no_value_message())

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


## @example onpremise/match_metrics.py
#
# The example illustrates the various metrics that can be obtained about the device detection
# process, for example, the degree of certainty about the result. Running the example outputs
# those properties and values.

# The example also illustrates controlling properties that are returned from the detection
# process - reducing the number of components required to return the properties requested reduces
# the overall time taken.
# 
# There is a [discussion](https://51degrees.com/documentation/_device_detection__hash.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=top#DeviceDetection_Hash_DataSetProduction_Performance)
# of metrics and controlling performance on our web site. See also the (performance options)
# [https://51degrees.com/documentation/_device_detection__features__performance_options.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=top]
# page.
# # Location
# This example is available in full on [GitHub](https://github.com/51Degrees/device-detection-python/blob/main/fiftyone_devicedetection_examples/fiftyone_devicedetection_examples/onpremise/match_metrics.py].

from itertools import groupby
from pathlib import Path
import sys
from fiftyone_devicedetection.devicedetection_pipelinebuilder import DeviceDetectionPipelineBuilder
from fiftyone_pipeline_core.logger import Logger
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_devicedetection_shared.example_constants import EVIDENCE_VALUES
from fiftyone_devicedetection_shared.example_constants import LITE_DATAFILE_NAME

class MatchMetricsConsole():
    
    def run(self, data_file, show_descs, logger, output):
        # Build a new Pipeline to use an on-premise Hash engine with the
        # low memory performance profile.
        pipeline = DeviceDetectionPipelineBuilder(
            data_file_path = data_file,
            # Inhibit auto-update of the data file for this example
            auto_update = False,
            licence_keys = "",
            # Prefer low memory profile where all data streamed from disk
            # on-demand. Experiment with other profiles.
            performance_profile = "LowMemory",
            #performance_profile = "HighPerformance",
            #performance_profile = "Balanced",
            # Disable share usage for this example.
            usage_sharing = False,
            # You can improve matching performance by specifying only those
            # properties you wish to use. If you don't specify any properties
            # you will get all those available in the data file tier that
            # you have used. The free "Lite" tier contains fewer than 20.
            # Since we are specifying properties here, we will only see
            # those properties, along with the match metric properties
            # in the output.
            restricted_properties=["ismobile", "hardwarename"],
            # Uncomment BrowserName to include Browser component profile ID
            # in the device ID value.
            #restricted_properties=["ismobile", "hardwarename", "browsername"],
            # If using the full on-premise data file this property will be
            # present in the data file. See https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=run
            # Only use the predictive graph to better handle variances
            # between the training data and the target User-Agent string.
            # For a more detailed description of the differences between
            # performance and predictive, see
            # https://51degrees.com/documentation/_device_detection__hash.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=run#DeviceDetection_Hash_DataSetProduction_Performance
            use_predictive_graph = True,
            use_performance_graph = False,
            # We want to show the matching evidence characters as part of this example, so we have to set
            # this flag to true.
            update_matched_useragent = True).add_logger(logger).build()
        
        ExampleUtils.check_data_file(pipeline, logger)

        data = pipeline.create_flowdata()

        # Process a single evidence to retrieve the values
        # associated with the user-agent and other evidence such as sec-ch-* for the
        # selected properties.
        data.evidence.add_from_dict(self.Evidence)
        data.process()

        device = data.device

        output("--- Compare evidence with what was matched ---\n")
        output("Evidence")
        # output the evidence in reverse value length order
        for entry in sorted(self.Evidence.items(), key=lambda item: len(item[1]), reverse=True):
            output(f"    {entry[0]}: {entry[1]}")
        # Obtain the matched User-Agents: the matched substrings in the
        # User-Agents are separated with underscores - output in forward length order.
        output("Matches")
        for entry in sorted(device.useragents.value(), key=lambda item: len(item)):
            output(f"    Matched User-Agent: {entry}")

        output("")


        output("--- Listing all available properties, by component, by property name ---")
        output("For a discussion of what the match properties mean, see: https://51degrees.com/documentation/_device_detection__hash.html?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=match-properties-discussion#DeviceDetection_Hash_DataSetProduction_Performance\n")

        # get the properties available from the DeviceDetection engine
        # which has the key "device". For the sake of illustration we will
        # retrieve it indirectly.
        hashEngineElementKey = pipeline.get_element("device").datakey

        # retrieve the available properties from the hash engine. The properties
        # available depends on
        # a) the use of restricted_properties in the builder (see above)
        # which controls which properties will be extracted, and also affects
        # the performance of extraction
        # b) the tier of data file being used. The Lite data file contains fewer
        # than 20 of the >200 available properties
        availableProperties = dict(pipeline.get_properties()[hashEngineElementKey])
        
        # create a Map keyed on the component name of the properties available
        # components being hardware, browser, OS and Crawler.
        def get_component(property):
            return property[1]["component"]

        availableProperties = dict(sorted(availableProperties.items(),key=lambda item: get_component(item)))
        categoryMap = groupby(availableProperties.items(), get_component)
        # iterate the map created above
        for component, properties in categoryMap:
            output(component)
            for propertyKey, property in properties:
                propertyName = property["name"]
                propertyDescription = property["description"]
                
                # while we get the available properties and their metadata from the
                # pipeline we get the values for the last detection from flowData
                value = device[propertyKey]
                
                # output property names, values and descriptions
                # some property values are lists.
                if value.has_value() and isinstance(value.value(), list):
                    output(f"    {propertyName}: {len(value.value())} Values")
                    for item in value.value():
                        output(f"        : {item}")

                else:
                    output(f"    {propertyName}: {value.value()}")

                if (show_descs == True):
                    output(f"        {propertyDescription}")

        output()
        logger.log("info", "Finished Match Metrics Example")
    
    # Evidence values from a windows 11 device using a browser
    # that supports User-Agent Client Hints.
    Evidence = EVIDENCE_VALUES[2]

def main(argv):
    # In this example, by default, the 51degrees "Lite" file needs to be
    # somewhere in the project space, or you may specify another file as
    # a command line parameter.
    #
    # Note that the Lite data file is only used for illustration, and has
    # limited accuracy and capabilities.
    # Find out about the Enterprise data file on our pricing page:
    # https://51degrees.com/pricing?utm_source=code&utm_medium=example&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_examples-src-fiftyone_devicedetection_examples-onpremise-match_metrics.py&utm_term=main
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file(LITE_DATAFILE_NAME)
    
    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    if (data_file != None):
        MatchMetricsConsole().run(data_file, False, logger, print)
    else:
        logger.log("error",
            "Failed to find a device detection data file. Make sure the " +
            "device-detection-data submodule has been updated by running " +
            "`git submodule update --recursive`.")

if __name__ == "__main__":
    main(sys.argv[1:])
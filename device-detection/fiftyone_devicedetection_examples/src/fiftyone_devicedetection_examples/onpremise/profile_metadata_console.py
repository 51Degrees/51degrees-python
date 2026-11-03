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

## @example onpremise/profile_metadata_console.py
# @brief Profile Metadata Console Example - On-premise
#
# This example demonstrates how to iterate through all hardware profiles in a
# 51Degrees on-premise data file and extract specific device properties
# (TAC, DeviceType, HardwareVendor, HardwareName, HardwareModel) via the
# metadata API.
#
# You will learn:
# 1. How to access the low-level SWIG engine directly
# 2. How to iterate through all profiles in the data file
# 3. How to filter profiles by component (HardwarePlatform)
# 4. How to extract property values for each profile via metadata
# 5. How to handle multi-value properties (TAC, HardwareName)
# 6. How to output the results as JSON
#
# Required PyPi Dependencies:
# - fiftyone_devicedetection_onpremise

import sys
import json
from fiftyone_devicedetection_onpremise.devicedetection_onpremise import (
    EngineHashSwig,
    ConfigHashSwig,
    RequiredPropertiesConfigSwig,
    VectorStringSwig
)
from fiftyone_devicedetection_examples.example_utils import ExampleUtils
from fiftyone_pipeline_core.logger import Logger


def flush_print(*args, **kwargs):
    """Print with immediate flush for progress visibility."""
    print(*args, **kwargs, flush=True)


def stderr_print(*args, **kwargs):
    """Print to stderr with immediate flush (for progress when JSON goes to stdout)."""
    print(*args, **kwargs, file=sys.stderr, flush=True)


class ProfileMetadataConsole():
    # Properties we want to extract from each hardware profile
    # Note: TAC, HardwareName, NativeName, NativeModel are multi-value properties (string[])
    TARGET_PROPERTIES = ["tac", "hardwarevendor", "hardwarename", "hardwaremodel", "nativemodel", "nativename"]

    # Properties that can have multiple values
    MULTI_VALUE_PROPERTIES = ["tac", "hardwarename", "nativename", "nativemodel"]

    def run(self, data_file, output_file, logger, output, limit=None):
        output(f"Loading data file: {data_file}")

        # Configure the engine with all properties (empty list = all available)
        # We use all properties because restricting properties affects what
        # values are accessible via metadata
        properties_list = RequiredPropertiesConfigSwig(VectorStringSwig())

        # Create configuration - use LowMemory since we're just reading metadata
        config = ConfigHashSwig()
        config.setLowMemory()
        config.setUseUpperPrefixHeaders(False)

        # Create the engine directly (not through pipeline)
        engine = EngineHashSwig(data_file, config, properties_list)

        # Get metadata
        metadata = engine.getMetaData()

        # Get all profiles
        profiles = metadata.getProfiles()
        profile_count = profiles.getSize()

        output(f"Found {profile_count} total profiles in data file")

        # Get the HardwarePlatform component to filter only hardware profiles
        components = metadata.getComponents()
        hardware_component_name = None
        output("Available components:")
        for i in range(components.getSize()):
            comp = components.getByIndex(i)
            output(f"  - {comp.getName()}")
            if comp.getName() == "HardwarePlatform":
                hardware_component_name = comp.getName()

        if hardware_component_name is None:
            output("Warning: Could not find HardwarePlatform component, processing all profiles")

        # Iterate through all profiles and stream results immediately
        hardware_profile_count = 0

        # Open output destination - file or stdout
        out_stream = open(output_file, 'w') if output_file else sys.stdout

        try:
            # Write JSON array opening bracket
            out_stream.write("[\n")

            output("Processing profiles...")

            for i in range(profile_count):
                if i > 0 and i % 1000 == 0:
                    output(f"  Processed {i}/{profile_count} profiles, found {hardware_profile_count} hardware profiles...")

                profile = profiles.getByIndex(i)

                # Check if this profile belongs to HardwarePlatform component
                if hardware_component_name is not None:
                    component = metadata.getComponentForProfile(profile)
                    if component.getName() != hardware_component_name:
                        continue

                # Apply limit to hardware profiles if specified
                if limit and hardware_profile_count >= limit:
                    break

                hardware_profile_count += 1

                # Get values for this profile
                values = metadata.getValuesForProfile(profile)

                # Build a record for this profile
                record = {
                    "profileId": profile.getProfileId()
                }

                # Extract each target property value
                # Multi-value properties will be accumulated into lists
                for j in range(values.getSize()):
                    value = values.getByIndex(j)
                    prop = metadata.getPropertyForValue(value)
                    prop_name = prop.getName().lower()

                    if prop_name in self.TARGET_PROPERTIES:
                        value_str = value.getName()

                        if prop_name in self.MULTI_VALUE_PROPERTIES:
                            # Accumulate multi-value properties into a list
                            if prop_name not in record:
                                record[prop_name] = []
                            record[prop_name].append(value_str)
                        else:
                            # Single-value property
                            record[prop_name] = value_str

                # Write comma separator before all records except the first
                if hardware_profile_count > 1:
                    out_stream.write(",\n")
                out_stream.write(json.dumps(record, indent=2))
                out_stream.flush()

            # Close the JSON array
            out_stream.write("\n]\n")

            output(f"Extracted {hardware_profile_count} hardware profiles")
            if output_file:
                output(f"Results written to: {output_file}")
        finally:
            if output_file and out_stream:
                out_stream.close()


def main(argv):
    # Default data file path - use TAC data file for enterprise features
    data_file = argv[0] if len(argv) > 0 else ExampleUtils.find_file("TAC-HashV41.hash")
    # Output file - use "-" for stdout
    output_arg = argv[1] if len(argv) > 1 else "-"
    output_file = None if output_arg == "-" else output_arg
    # Optional limit on number of hardware profiles to process
    limit = int(argv[2]) if len(argv) > 2 else None

    # Configure a logger to output to the console.
    logger = Logger(min_level="info")

    # Use stderr for progress when JSON goes to stdout
    output_func = flush_print if output_file else stderr_print

    if data_file is not None:
        ProfileMetadataConsole().run(data_file, output_file, logger, output_func, limit)
    else:
        logger.log("error",
            "Failed to find a device detection data file. " +
            "Please provide the path to a TAC-HashV41.hash file as the first argument.")


if __name__ == "__main__":
    main(sys.argv[1:])

# 51Degrees Device Detection Engines - Examples

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **v4 Device Detection Python**

[Developer Documentation](https://51degrees.com/documentation/_device_detection__quickstart.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-readme.md&utm_term=51degrees-device-detection-engines-examples "Developer Documentation") | [Available Properties](https://51degrees.com/resources/property-dictionary?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-readme.md&utm_term=51degrees-device-detection-engines-examples "View all available properties and values")

## Introduction

This project contains examples for the 51Degrees device detection engines contained in this repository.
Then you will be able to run the examples directly:

## Examples

Any of the examples in this project can be run by calling python directly. For example, to run the cloud
getting started example:

`python -m fiftyone_devicedetection_examples.cloud.gettingstarted_console`

The on-premise examples use the free Lite data file by default. The data
repository, at `cxx/data`, links to it, and an example downloads it the
first time it is missing, so the examples run from a fresh clone with no
settings. Where an example shows a property that only the Enterprise data
file has, such as HardwareVendor, HardwareName or DeviceType, it shows the
property as needing the Enterprise data file and gives a link to
[contact us](https://51degrees.com/contact-us?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_devicedetection_examples-readme.md&utm_term=enterprise-data-file)
about a copy. Supply the path to an Enterprise data file as the first
command line argument to see every property.

The data file update example needs a licence key, and the hardware profile
examples need the TAC data file or its CSV export, so without them each one
says what it needs and where to ask for it, and stops.

## Web examples

The `gettingstarted_web` and `useragentclienthints_web` examples, under
`cloud` and `onpremise`, are Flask web applications. A Flow Data cannot be
used by two threads at once, so each of them creates a Flow Data for each
request, uses it only in the code that handles that request, and closes it
when the request ends. To hand work to another thread or task, read the
values it needs from the Flow Data first and pass those values, not the
Flow Data.

## Tests

To run the tests use:

`python -m unittest discover -s tests -p test*.py -b`

The tests in `tests/test_examples_without_settings.py` run the on-premise
examples as they run from a fresh clone, with no licence key, and check that
each one finishes on the free Lite data file and gives the link to ask for
the Enterprise data file.

The cloud tests need a valid 51Degrees resource key (see above), and skip
without one. They read it from the environment variable
`_51DEGREES_RESOURCE_KEY_BESPOKE`, and give it to each example under
`_51DEGREES_RESOURCE_KEY`, the name the examples read. They are marked
`live`, so `python -m pytest -m "not live"` runs every other test, which is
what CI does when no resource key is passed.

For example, use following command to set the resource key for the tests on
Linux:
`export _51DEGREES_RESOURCE_KEY_BESPOKE=MY-RESOURCE-KEY`

On Microsoft Windows use:
`$env:_51DEGREES_RESOURCE_KEY_BESPOKE = "MY-RESOURCE-KEY"`

As the performance and offline processing tests take longer than the others, there is another environment variable flag to run those:

Linux:
`export _51DEGREES_RUN_PERFORMANCE_TESTS=true`

Microsoft Windows:
`$env:_51DEGREES_RUN_PERFORMANCE_TESTS = "true"`

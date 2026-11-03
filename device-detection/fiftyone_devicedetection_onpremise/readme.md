# 51Degrees Device Detection Engines - On-Premise

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_onpremise-readme.md&utm_term=51degrees-device-detection-engines-on-premise "THE Fastest and Most Accurate Device Detection") **v4 Device Detection Python**

[Developer Documentation](https://51degrees.com/device-detection-python/index.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_onpremise-readme.md&utm_term=51degrees-device-detection-engines-on-premise "Developer Documentation") | [Available Properties](https://51degrees.com/resources/property-dictionary?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_onpremise-readme.md&utm_term=51degrees-device-detection-engines-on-premise "View all available properties and values")

## Introduction

This project contains the 51Degrees On-Premise Device Detection Engines for Python which can be used with the Pipeline API.

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines) 

This engine is a C++ library with a Python wrapper built using [SWIG](http://www.swig.org/).

## Requirements

* Python 3.8+
* One of the following supported platforms:
  * Windows Server 2019 / Windows 10
  * Ubuntu 18.04
  * MacOS X Mojave 10.14
* C/C++ Compiler
  * VS2015+
  * GCC 7.4+
  * Clang/LLVM 11.0.0+
* The 'atomic' library on Linux platform for GCC
* The `Cython` python library
* The `flask` python library to run the web examples
* Python3 Dev Package is also required to build extensions on Linux and MacOS  

## Installation

The extension requires that you have set up the required build tools for your platform.

### Prerequisites

#### Windows

### From PyPi

`pip install fiftyone_devicedetection_onpremise`

You can confirm this is working with the following micro-example.

* Run the example with `python exampledd.py`
* Feel free to try different user-agents and property values.

```python
from fiftyone_devicedetection_onpremise.devicedetection_onpremise_pipelinebuilder import DeviceDetectionOnPremisePipelineBuilder
pipeline = DeviceDetectionOnPremisePipelineBuilder(
  data_file_path = /path/to/hash/data/file, licence_keys = "", 
  ).build()
fd = pipeline.create_flowdata()
fd.evidence.add("header.user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
fd.process()
print(fd.device.ismobile.value())
```

For more in-depth examples, check out the [examples](https://51degrees.com/device-detection-python/examples.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_onpremise-readme.md&utm_term=from-pypi) page in the documentation.

### From GitHub

If you've cloned the GitHub repository, you will need to build the extension. Make sure Python3 Dev Package is installed if you are using Linux or MacOS.

```bash
cd fiftyone_devicedetection_onpremise/
python setup.py build_clib build_ext
python -m pip install -e .
```

#### Examples

If you've cloned the GitHub repository, you will be able to run the examples in the `fiftyone_devicedetection_examples` directory.

## Tests

To run the tests use:

`python -m unittest discover -s tests -p test*.py -b`

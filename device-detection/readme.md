# 51Degrees Device Detection Engines

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=51degrees-device-detection-engines "THE Fastest and Most Accurate Device Detection") **v4 Device Detection Python**

[Developer Documentation](https://51degrees.com/device-detection-python/index.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=51degrees-device-detection-engines "Developer Documentation") | [Available Properties](https://51degrees.com/resources/property-dictionary?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=51degrees-device-detection-engines "View all available properties and values")

## Introduction

This project contains 51Degrees Device Detection engines that can be used with the Pipeline API.

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines)

This git repository uses submodules, to clone the git repository run:

```bash
git clone --recurse-submodules https://github.com/51Degrees/device-detection-python.git
```

or if already cloned run the following to obtain all sub modules:

```bash
git submodule update --init --recursive
```

## Dependencies

For runtime dependencies, see our [dependencies](https://51degrees.com/documentation/_info__dependencies.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=dependencies) page.
The [tested versions](https://51degrees.com/documentation/_info__tested_versions.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=dependencies) page shows 
the Python versions that we currently test against. The software may run fine against other versions, 
but additional caution should be applied.

### Data

The API can either use our cloud service to get its data or it can use a local (on-premise) copy of the data.

#### Cloud

You will require a [resource key](https://51degrees.com/documentation/_info__resource_keys.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=cloud)
to use the Cloud API. You can create resource keys using our 
[configurator](https://configure.51degrees.com/?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=cloud), see our 
[documentation](https://51degrees.com/documentation/_concepts__configurator.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=cloud) on how to use this.

#### On-Premise

In order to perform device detection on-premise, you will need to use a 51Degrees data file. 
This repository includes a free, 'lite' file in the 'device-detection-data' sub-module that has a 
significantly reduced set of properties. To obtain a file with a more complete set of device 
properties see the [51Degrees website](https://51degrees.com/pricing?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=readme.md&utm_term=on-premise). If you want to use the lite 
file, you will need to install [GitLFS](https://git-lfs.github.com/):

```
sudo apt-get install git-lfs
git lfs install
```

Then, navigate to 'src/fiftyone_devicedetection_onpremise/cxx/device-detection-data' and execute:

```
git lfs pull
```

## Folders

* `fiftyone_devicedetection` - references both cloud and on-premise packages, contains generic Device-Detection Pipeline Builder.
  * `examples` - examples for switching between cloud and on-premise.
* `fiftyone_devicedetection_cloud` - cloud implementation of the engines.
  * `tests` - tests for the cloud engine and examples.
* `fiftyone_devicedetection_onpremise` - uses a native library which is built during setup to provide optimal performance and low latency device detections.
  * `tests` - tests for the on-premise engine.
* `fiftyone_devicedetection_shared` - common components used by the cloud and on-premise packages.
* `fiftyone_devicedetection_examples` - cloud and on-premise examples.
  * `tests` - tests for the examples.

## Installation

### PyPi

To install all packages, run:

```bash
python -m pip install fiftyone-devicedetection
```

The `fiftyone-devicedetection` package references both cloud and on-premise packages. If you do 
not want the on-premise engine or cannot meet the requirements for installing on-premise then 
install the cloud package on its own:

```bash
python -m pip install fiftyone-devicedetection-cloud
```
or
```bash
python -m pip install fiftyone-devicedetection-onpremise
```

See the [cloud](fiftyone_devicedetection_cloud/readme.md) and 
[onpremise](fiftyone_devicedetection_onpremise/readme.md) package readmes for more detail.

### Build from Source

Device detection on-premise uses a native binary. (i.e. compiled from C code to target a specific 
platform/architecture) This section explains how to build this binary.

#### Pre-requisites

- Install C build tools:
  - Windows:
    - You will need either Visual Studio 2019 or the [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) installed.
      - Minimum platform toolset version is `v142`
      - Minimum Windows SDK version is `10.0.18362.0`
  - Linux/MacOS:
    - `sudo apt-get install g++ make libatomic1`
- If you have not already done so, pull the git submodules that contain the native code:
  - `git submodule update --init --recursive`

#### Build steps

It is recommended to use Pipenv when building packages. Pipenv will ensure all the required packages 
for building and testing are available e.g. `cython` and `flask`.

```bash
python -m pip install pipenv
pipenv install
pipenv shell
```

We use `make` to manage the build process. There are several targets for the make process. 
If unsure, you probably want to use the `install` target: 

```bash
make install
```

other make targets:

* `cloud` - only setup packages required for cloud
* `onpremise` - only setup packages required for onpremise
* `test` - run package tests
* `clean` - remove temporary files created when building extensions

Make can be installed on Windows. Alternatively, there is also a powershell setup script called 
`setup.ps1`. To run it, you may need to update the execution policy to allow unsigned scripts to 
execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser Bypass

.\setup.ps1
```

Finally, if the make or powershell scripts fail, or you want to perform the steps manually for 
some other reason, these are the commands to build the native on-premise library and install 
the packages.

```bash
python -m pip install -e fiftyone_devicedetection_shared/
python -m pip install -e fiftyone_devicedetection_cloud/
cd fiftyone_devicedetection_onpremise/
python setup.py build_clib build_ext
cd ../
python -m pip install -e fiftyone_devicedetection_onpremise/
python -m pip install -e fiftyone_devicedetection/
```

## Examples

### Prerequisites
Please install the pre-requisites listed above as well as the examples themselves as a package:
```bash
python -m pip install -e fiftyone_devicedetection_examples/
python -m pip install -e fiftyone_devicedetection_shared/
```

### Running examples
To run an example - run a corresponding Python module specifying its full namespace.  
For cloud examples please provide a `resource_key` as an environment variable, f.e.:

```bash
resource_key=<your_resource_key> python -m fiftyone_devicedetection_examples.cloud.gettingstarted_console
```

For some of the onpremise examples you might need to provide a `license_key` as an environment variable, f.e.:
```bash
license_key=<your_license_key> python -m fiftyone_devicedetection_examples.onpremise.datafileupdate_console
```

```bash
python -m fiftyone_devicedetection_examples.cloud.gettingstarted_console
```

Please see a full list of provided cloud and onpremise examples below.

### Cloud

| Example                                | Description |
|----------------------------------------|-------------|
| gettingstarted_console                 | How to use the 51Degrees Cloud service to determine details about a device based on its User-Agent and User-Agent Client Hints HTTP header values. |
| gettingstarted_web                     | How to use the 51Degrees Cloud service to determine details about a device as part of a simple ASP.NET website. |
| taclookup_console                              | How to get device details from a TAC (Type Allocation Code) using the 51Degrees cloud service. |
| nativemodellookup_console                      | How to get device details from a native model name using the 51Degrees cloud service. |
| failuretomatch                         | Demonstrate the features that are available when a match cannot be found. |
| metadata_console                       | How to access the meta-data for the device detection data model. For example, information about the  available properties. |
| useragentclienthints_web               | How to use the 51Degrees Cloud service to perform device detection from User-Agent Client Hints, including the Accept-CH header round trip, in a simple Flask website. |

### On-Premise

| Example                                | Description |
|----------------------------------------|-------------|
| gettingstarted_console                 | How to use the 51Degrees on-premise device detection API to determine details about a device based on its User-Agent and User-Agent Client Hints HTTP header values. |
| gettingstarted_web                     | How to use the 51Degrees Cloud service to determine details about a device as part of a simple ASP.NET website. |
| failuretomatch                         | Demonstrate the features that are available when a match cannot be found. |
| match_metrics                          | How to access the metrics that relate to the device detection algorithm. |
| metadata_console                       | How to access the meta-data for the device detection data model. For example, information about the  available properties. |
| offlineprocessing                    | Example showing how to ingest a file containing data from web requests and perform detection against the entries. |
| performance                           | How to configure the various performance options and run a simple performance test. |
| useragentclienthints_web              | How to use the 51Degrees on-premise device detection API to perform device detection from User-Agent Client Hints, including the Accept-CH header round trip, in a simple Flask website. |
| datafileupdate_console                | How to automatically update data file |
| profile_metadata_console              | How to iterate through all hardware profiles in a data file and extract device properties (TAC, HardwareVendor, HardwareName, etc.) via the SWIG metadata API. |
| csv_profile_metadata                  | How to read hardware profile data from the 51Degrees HardwarePlatform CSV export file and output selected properties as JSON. Much faster than the metadata API approach. |
| shareusage                            | How to use the ShareUsage element directly to send evidence data to 51Degrees for usage sharing. |


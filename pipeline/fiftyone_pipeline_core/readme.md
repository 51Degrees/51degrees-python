# Pipeline Core

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python Pipeline Core**

[Developer Documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core&utm_term=pipeline-core "Developer Documentation")

## Introduction

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines) 

## This package fiftyone_pipeline_core

This package defines the essential components of the Pipeline API such as `flow elements`, `flow data` and `evidence`. It also packages together JavaScript served by a pipeline and allows for client side requests for additional data populated by evidence from the client side.

It can be used on its own or with the following additional packages.

- **fiftyone_pipeline_engines** - Adds a specialized type of flow element called an engine which allows for additional features including an auto-updating data file for properties, a service called when a requested property is missing and a caching system.

Engines created by 51Degrees:

- [**fiftyone_devicedetection**](https://pypi.org/project/fiftyone-devicedetection/) - Get details about the devices accessing your web page
- [**fiftyone_location**](https://pypi.org/project/fiftyone-location/) - Get postal address details from the location of devices accessing your web page

## Requirements

* Python 3.8+
* The `flask` python library to run the web examples

## Find out more

- [Build your own](https://51degrees.com/build-your-own?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core&utm_term=find-out-more-build-your-own)
- [Pipeline API documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core&utm_term=find-out-more-documentation)
- [Pipeline API examples](https://51degrees.com/documentation/_pipeline_api__examples__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_core&utm_term=find-out-more-examples)
- https://github.com/51Degrees/51degrees-python

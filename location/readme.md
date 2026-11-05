# 51Degrees Geo-Location Engines

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") 
**v4 Location Python**

[Developer Documentation](https://51degrees.com/documentation/_reverse_geocoding__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=51degrees-geo-location-engines "Developer documentation")

## Introduction

This project contains the geo-location engines for the Python implementation of the 51Degrees Pipeline API.

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines) 

## Dependencies

The [tested versions](https://51degrees.com/documentation/_product_summaries__tested_versions.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=dependencies) page shows the Python versions that we currently test against. The software may run fine against other versions, but additional caution should be applied.

## Installation and Examples

### From PyPI

`pip install fiftyone-location`

You can confirm this is working with the following micro-example.

* Create a resource key for free with the 51Degrees [configurator](https://configure.51degrees.com/6CTsmbPx?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=from-pypi). This defines the properties you want to access.
* On the 'implement' page of the configurator, copy the resource key and replace YOUR_RESOURCE_KEY in the example below. Save this as examplelocation.py
* Run the example with `python examplelocation.py`
* Feel free to try different locations and property values.

```
from fiftyone_location.location_pipelinebuilder import LocationPipelineBuilder
pipeline = LocationPipelineBuilder(resource_key="YOUR_RESOURCE_KEY").build()
fd = pipeline.create_flowdata()
fd.evidence.add("query.51D_Pos_latitude", "40.730610")
fd.evidence.add("query.51D_Pos_longitude", "-73.935242")
fd.process()
print(fd.location.town.value())
```

For more in-depth examples, the following are included with this repository:

| Example                                | Description |
| gettingstarted.py                      | Demonstrates the basics of using the service to get postal address information from coordinates. |
| web.py                                 | Shows how to use the location service as part of a simple website. |

### From GitHub

If you've cloned the GitHub repository, you will be able to run the examples directly:

`python -m examples.cloud.gettingstarted`

To run the web example navigate into Examples folder:

#### Linux

Execute `export FLASK_APP=web` where `web` is the example file, and start your application via `flask run`.

#### Windows

Execute `$env:FLASK_APP = "web"` where `web` is the example file, and start your application via `flask run`.

## Find out more

- [Geolocation](https://51degrees.com/geolocation?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=find-out-more-geolocation)
- [Reverse geocoding documentation](https://51degrees.com/documentation/_reverse_geocoding__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=find-out-more-documentation)
- [Getting started](https://51degrees.com/documentation/_reverse_geocoding__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=find-out-more-getting-started)
- [Pricing](https://51degrees.com/pricing?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_location&utm_term=find-out-more-pricing)
- https://github.com/51Degrees/51degrees-python

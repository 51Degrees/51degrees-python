# Pipeline Translation

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python Pipeline Translation**

[Developer Documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_translation&utm_term=pipeline-translation "Developer Documentation")

## Introduction

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines)

## Requirements

* Python 3.8+

## This package fiftyone_pipeline_translation

This package adds a generic translation flow element to the pipeline. It takes
string based values from a single source element (a plain string, a list of
strings, or a weighted list of strings) and translates them into another
language using YAML translation files. The language to translate to can be
fixed, or resolved from the request evidence (for example an `Accept-Language`
header).

This package is built on top of:

* [fiftyone_pipeline_core](https://pypi.org/project/fiftyone-pipeline-core/)

## Find out more

- [Build your own](https://51degrees.com/build-your-own?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_translation&utm_term=find-out-more-build-your-own)
- [Pipeline API documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_translation&utm_term=find-out-more-documentation)
- [Pipeline API examples](https://51degrees.com/documentation/_pipeline_api__examples__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_translation&utm_term=find-out-more-examples)
- https://github.com/51Degrees/51degrees-python

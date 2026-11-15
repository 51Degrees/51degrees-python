# Pipeline Derived Properties

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python Pipeline Derived Properties**

[Developer Documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty&utm_term=pipeline-derived-properties "Developer Documentation")

## Introduction

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines)

## Requirements

* Python 3.10+

## This package fiftyone_pipeline_derivedproperty

This package adds the derived property flow element to the pipeline. It computes new properties from properties other elements have already put into the flow data, such as HumanConfidence from Device Detection and IP Intelligence properties, and IsGdpr from the country of an IP address. It holds no data file, sends no request and reads no evidence.

Each property is defined by a script in the format the [derived-properties](https://github.com/51Degrees/derived-properties) repository describes, written in YAML or JSON. The scripts that repository holds are built into this package, and the same scripts give the same answers in every 51Degrees language, which the case files in that repository prove. Every script writes one property under the element data key `derived`.

Where a property a script reads is not available, the derived property has no value, and reading it raises a message naming every property that was missing and why.

This package is built on top of:

* [fiftyone_pipeline_core](https://pypi.org/project/fiftyone-pipeline-core/)

## Scripts

A script built into the package is named by its name. A script of your own is given as a file, where the file name may hold a wildcard, or as text held by your code. The script's `Name` must equal its file name without the extension, or the name given with the text.

```python
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_derivedproperty import (
    DerivedPropertyElementBuilder, builtin_script_names)

print(builtin_script_names())  # ['HumanConfidence', 'IsGdpr']

derived = (DerivedPropertyElementBuilder()
           # A script built into this package.
           .add_built_in_script("IsGdpr")
           # A file, or several files, from your own environment.
           .add_script_file("derived/*.yaml")
           # The text of a script held by your own code, YAML or JSON.
           .add_script("MyProperty", script_text)
           .build())

# Add the element after the elements that supply what its scripts read.
pipeline = (PipelineBuilder()
            .add(ip_intelligence_engine)
            .add(derived)
            .build())

flowdata = pipeline.create_flowdata()
flowdata.evidence.add_from_dict(evidence)
flowdata.process()
is_gdpr = flowdata.derived.IsGdpr
print(is_gdpr.value() if is_gdpr.has_value() else is_gdpr.no_value_message())
```

Every fault in every script is reported together when the element is built, in a `ScriptValidationError` whose `faults` list each one.

## Configuration

A pipeline configuration names the element with `elementPath` `fiftyone_pipeline_derivedproperty` and `elementName` `DerivedPropertyElement`. Its settings are `scripts`, naming scripts built into the package, and `script_files`, giving paths to script files. Each is a list of strings, or one string with commas between the entries, where an entry holding a comma is wrapped in double quotes. The setting names are matched without regard to case or underscores, so `Scripts` and `ScriptFiles` as the other languages write them work too, and any other setting is refused.

```json
{
  "PipelineOptions": {
    "Elements": [
      {
        "elementPath": "fiftyone_pipeline_derivedproperty",
        "elementName": "DerivedPropertyElement",
        "elementParameters": { "scripts": "IsGdpr", "script_files": "derived/*.yaml" }
      }
    ]
  }
}
```

IsGdpr reads `ip.CountryCode`, so the pipeline also needs an element giving that, such as the IP Intelligence cloud engine or the on-premise engine with a data file that has the property. The free Lite IP Intelligence data file does not have it, so the element refuses a pipeline built on that file, as the next section describes.

## When the pipeline is built

The element refuses, with a `PipelineConfigurationError`, a pipeline in which no element supplies a property a script reads, or in which another element already writes a property a script writes. Where an element sits in the pipeline is not judged, so an element supplying a property that runs after this one builds, and on each request the derived property then has no value. That is logged once, at error level.

When the pipeline is built, the element logs one line for each script at information level, naming the script, its version, its format, where it came from and the property it writes, a warning for a script marked deprecated, and the compiled script as JSON at debug level.

## Installation

The package is not yet published to PyPI. To use it from this repository, clone the repository with its submodules, because the built in scripts are the `scripts` folder of the `derived-properties` submodule.

```
git clone --recurse-submodules https://github.com/51Degrees/51degrees-python.git
```

## Tests

The tests run every case file in the `tests` folder of the `derived-properties` submodule, including the scripts under `tests/invalid` that every language must refuse, with `python -m tox` in this folder.

## Find out more

- [Build your own](https://51degrees.com/build-your-own?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty&utm_term=find-out-more-build-your-own)
- [Pipeline API documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty&utm_term=find-out-more-documentation)
- https://github.com/51Degrees/derived-properties
- https://github.com/51Degrees/51degrees-python

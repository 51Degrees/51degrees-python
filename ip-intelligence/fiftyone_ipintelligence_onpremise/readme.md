# 51Degrees IP Intelligence Engines - OnPremise

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_onpremise-readme.md&utm_term=51degrees-ip-intelligence-engines-onpremise "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/ip-intelligence-python/index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_onpremise-readme.md&utm_term=51degrees-ip-intelligence-engines-onpremise "developer documentation")

## Introduction

This package resolves IP addresses to location, network and registration
information using a local `.ipi` data file and the
[51Degrees Pipeline API](https://51degrees.com/documentation/index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_onpremise-readme.md&utm_term=introduction).

The native [51degrees-cxx](https://github.com/51Degrees/51degrees-cxx/blob/main/docs/ipi/README.md)
library is included as a git submodule and wrapped with SWIG.

## Building

The SWIG generated wrapper (`ipi_python_wrap.cxx` and
`IpIntelligenceEngineModule.py`) is committed to the repository so SWIG is
only needed when regenerating it (run `PreBuild.bat` / `PreBuild.sh`).

A C++17 compiler is required to build the native extension:

```
git submodule update --init --recursive
python setup.py build_clib build_ext
```

## Data files

The on-premise engine requires a `.ipi` data file. The free Lite data file,
`51Degrees-LiteV41.ipi`, is linked from the
[data](https://github.com/51Degrees/data) repository, which is included as
the nested submodule `cxx/data` and contains evidence files for testing. From
the root of a checkout of
[51degrees-python](https://github.com/51Degrees/51degrees-python), download it
by running `sh cxx/data/get-data-files.sh 51Degrees-LiteV41.ipi`, or
`./cxx/data/get-data-files.ps1 51Degrees-LiteV41.ipi` in PowerShell. Without a
checkout, download it from
https://distributor.51degrees.com/api/v2/free/ipi-lite-v41, which sends it
gzip compressed.

## Usage

```python
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder

pipeline = IpIntelligenceOnPremisePipelineBuilder(
    data_file_path="51Degrees-LiteV41.ipi",
    licence_keys="",
    usage_sharing=False).build()

flowdata = pipeline.create_flowdata()
flowdata.evidence.add("query.client-ip", "185.28.167.78")
flowdata.process()
print(flowdata.ip.registeredname.value())
```

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

The on-premise engine requires a `.ipi` data file. A Lite data file can be
downloaded from
[51Degrees](https://51ddatafiles.blob.core.windows.net/enterpriseipi/51Degrees-LiteIpiV41.ipi.gz),
see also the [ip-intelligence-data](https://github.com/51Degrees/ip-intelligence-data)
repository which is included as a nested submodule and contains evidence
files for testing.

## Usage

```python
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise_pipelinebuilder import IpIntelligenceOnPremisePipelineBuilder

pipeline = IpIntelligenceOnPremisePipelineBuilder(
    data_file_path="51Degrees-LiteIpiV41.ipi",
    licence_keys="",
    usage_sharing=False).build()

flowdata = pipeline.create_flowdata()
flowdata.evidence.add("query.client-ip", "185.28.167.78")
flowdata.process()
print(flowdata.ip.registeredname.value())
```

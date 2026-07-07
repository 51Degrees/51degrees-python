# 51Degrees IP Intelligence Engines

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=repository&utm_content=readme_main&utm_campaign=python-open-source "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/ip-intelligence-python/index.html?utm_source=github&utm_medium=repository&utm_content=documentation&utm_campaign=python-open-source "developer documentation")

## Introduction

This package aggregates the cloud and on-premise 51Degrees IP intelligence
engines for the [51Degrees Pipeline API](https://51degrees.com/documentation/index.html)
and provides the `IpIntelligencePipelineBuilder` which builds a pipeline with
either engine depending on the settings provided:

- Provide a `resource_key` to use the cloud engine.
- Provide a `data_file_path` pointing at a `.ipi` data file to use the
  on-premise engine.

## Usage

```python
from fiftyone_ipintelligence.ipintelligence_pipelinebuilder import IpIntelligencePipelineBuilder

# Cloud
pipeline = IpIntelligencePipelineBuilder(resource_key="YOUR_RESOURCE_KEY").build()

# On-premise
pipeline = IpIntelligencePipelineBuilder(
    data_file_path="51Degrees-LiteIpiV41.ipi",
    licence_keys="",
    usage_sharing=False).build()

flowdata = pipeline.create_flowdata()
flowdata.evidence.add("query.client-ip", "185.28.167.78")
flowdata.process()
print(flowdata.ip.registeredname.value())
```

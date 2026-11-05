# 51Degrees IP Intelligence Engines

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/documentation/_ip_intelligence__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=51degrees-ip-intelligence-engines "developer documentation")

## Introduction

This package aggregates the cloud and on-premise 51Degrees IP intelligence
engines for the [51Degrees Pipeline API](https://51degrees.com/documentation/index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=introduction)
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

## Find out more

- [IP Intelligence](https://51degrees.com/ip-intelligence?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=find-out-more-ip-intelligence)
- [IP Intelligence documentation](https://51degrees.com/documentation/_ip_intelligence__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=find-out-more-documentation)
- [Getting started](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=find-out-more-getting-started)
- [Pricing](https://51degrees.com/pricing?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence&utm_term=find-out-more-pricing)
- https://github.com/51Degrees/51degrees-python

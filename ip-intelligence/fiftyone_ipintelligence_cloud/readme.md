# 51Degrees IP Intelligence Engines - Cloud

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=51degrees-ip-intelligence-engines-cloud "developer documentation")

## Introduction

This package uses the 51Degrees cloud service to resolve IP addresses to
location, network and registration information using the
[51Degrees Pipeline API](https://51degrees.com/documentation/index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=introduction).

To use the cloud service you will need a resource key. You can obtain one
from the [51Degrees Configurator](https://configure.51degrees.com/?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=introduction).

## Usage

```python
from fiftyone_ipintelligence_cloud.ipintelligence_cloud_pipelinebuilder import IpIntelligenceCloudPipelineBuilder

pipeline = IpIntelligenceCloudPipelineBuilder(resource_key="YOUR_RESOURCE_KEY").build()

flowdata = pipeline.create_flowdata()
flowdata.evidence.add("query.client-ip-51d", "185.28.167.78")
flowdata.process()

print(flowdata.ip.registeredname.value())
```

## Folders

- `fiftyone_ipintelligence_cloud` - the IP intelligence cloud engine and
  pipeline builder.
- `tests` - unit tests. These mock the cloud service so no resource key is
  required; set the `resource_key` environment variable to also run the live
  cloud integration test.

## Find out more

- [IP Intelligence](https://51degrees.com/ip-intelligence?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=find-out-more-ip-intelligence)
- [IP Intelligence documentation](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=find-out-more-documentation)
- [Getting started](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=find-out-more-getting-started)
- [Pricing](https://51degrees.com/pricing?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_cloud&utm_term=find-out-more-pricing)
- https://github.com/51Degrees/51degrees-python

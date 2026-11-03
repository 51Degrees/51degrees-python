# 51Degrees IP Intelligence Engines - Cloud

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=repository&utm_content=readme_main&utm_campaign=python-open-source "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/ip-intelligence-python/index.html?utm_source=github&utm_medium=repository&utm_content=documentation&utm_campaign=python-open-source "developer documentation")

## Introduction

This package uses the 51Degrees cloud service to resolve IP addresses to
location, network and registration information using the
[51Degrees Pipeline API](https://51degrees.com/documentation/index.html).

To use the cloud service you will need a resource key. You can obtain one
from the [51Degrees Configurator](https://configure.51degrees.com/).

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

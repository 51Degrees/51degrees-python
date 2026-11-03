# 51Degrees Device Detection Engines - Cloud

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-readme.md&utm_term=51degrees-device-detection-engines-cloud "THE Fastest and Most Accurate Device Detection") **v4 Device Detection Python**

[Developer Documentation](https://51degrees.com/device-detection-python/index.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-readme.md&utm_term=51degrees-device-detection-engines-cloud "Developer Documentation") | [Available Properties](https://51degrees.com/resources/property-dictionary?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-readme.md&utm_term=51degrees-device-detection-engines-cloud "View all available properties and values")

## Introduction

### From PyPi

`pip install fiftyone-devicedetection-cloud`

You can confirm this is working with the following micro-example.

* Create a resource key for free with the 51Degrees [configurator](https://configure.51degrees.com/np5M4nlF?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-readme.md&utm_term=from-pypi). This defines the properties you want to access.
* On the 'implement' page of the configurator, copy the resource key and replace YOUR_RESOURCE_KEY in the example below. Save this as exampledd.py
* Run the example with `python exampledd.py`
* Feel free to try different user-agents and property values.

```python
from fiftyone_devicedetection_cloud.devicedetection_cloud_pipelinebuilder import DeviceDetectionCloudPipelineBuilder
pipeline = DeviceDetectionCloudPipelineBuilder({"resource_key": "YOUR_RESOURCE_KEY"}).build()
fd = pipeline.create_flowdata()
fd.evidence.add("header.user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
fd.process()
print(fd.device.ismobile.value())
```

For more in-depth examples, check out the [examples](https://51degrees.com/device-detection-python/examples.html?utm_source=github&utm_medium=readme&utm_campaign=device-detection-python&utm_content=fiftyone_devicedetection_cloud-readme.md&utm_term=from-pypi) page in the documentation.

### From GitHub

#### Examples

If you've cloned the GitHub repository, you will be able to run the examples in the `fiftyone_devicedetection_examples` directory.

## Tests

To run the tests use:

`python -m unittest discover -s tests -p test*.py -b`



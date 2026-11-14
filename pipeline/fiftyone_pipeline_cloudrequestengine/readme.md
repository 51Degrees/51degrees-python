# Cloud Request Engine

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python Pipeline Cloud Request Engine**

[Developer Documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=cloud-request-engine "Developer Documentation")

## Introduction

The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines) 

## Requirements

* Python 3.8+

## This package fiftyone_pipeline_cloudrequestengine

This package uses the `engines` class created by the `fiftyone-pipeline-engines`. It makes available:

* A `Cloud Request Engine` which calls the 51Degrees cloud service to fetch properties and metadata about them based on a provided resource key. Get a resource key at https://51degrees.com/configure/?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=this-package-fiftyone_pipeline_cloudrequestengine
* A `Cloud Engine` template which reads data from the Cloud Request Engine.

## Credentials

The engine authenticates with a resource key, a licence key, or both, set
as `resource_key` and `license_key` in its settings. Which one is set
decides whether `requested_properties`, the list of fully qualified
property names to ask for, is also needed:

| `resource_key` | `license_key` | `requested_properties` | Accepted |
| --- | --- | --- | --- |
| Yes | No | No | Yes. The resource key states which properties it carries. |
| Yes | Yes | No | Yes. The answer holds what the resource key carries. |
| Yes | Yes | Yes | Yes. The service adds the listed properties the licence key grants. |
| Yes | No | Yes | Yes. The service adds the listed properties, as null with a reason where no licence grants one. |
| No | Yes | Yes | Yes. A licence key names no properties, so the list says which are wanted. |
| No | Yes | No | No. The service answers 400 to every such request. |
| No | No | Either | No. There is nothing to authenticate with. |

A combination that is not accepted raises `ValueError` when the engine is
built, so a deployment sees one configuration error rather than a failure
on every request. A value that is empty or only whitespace counts as
absent, and each value is trimmed, so a key read from an environment
variable with a trailing newline still works.

A resource key is public by design, because it travels to the browser in a
script URL. A caller that runs only on the server should use a licence
key and name the properties it wants, so the credential stays on the
server and each answer carries only what that caller needs. A licence key
is sent in the body of every request, never in a URL. Where a request
named properties and the answer left some out, the engine warns once that
they are not covered by the keys in use, and the properties that came back
are usable as normal. With a resource key and no licence key, a property no
licence grants comes back as null with a reason, so the warning says instead
that every property is answered and these names are not properties, and
asks the caller to check the spelling of each one.

See the [Credentials section of the cloud request engine specification](https://github.com/51Degrees/specifications/blob/main/pipeline-specification/pipeline-elements/cloud-request-engine.md#credentials)
and the rules in
[`cloudrequestengine.py`](src/fiftyone_pipeline_cloudrequestengine/cloudrequestengine.py).

## When the engine is built

The engine asks the cloud service for the properties the key carries and
the evidence keys the service accepts when it is constructed, so a
pipeline built with it has both before the first request. When the cloud
service refuses either request, with an answer from 400 to 499 such as
the one for a resource key that is not valid, the constructor raises
`CloudRequestException`. Any other failure, such as the service being
unreachable, a timeout or an answer of 500 or more, gives a warning and
the engine is still built, so a cloud outage does not stop the
application starting. The engine then asks again when it is first used,
and a failure at that point is an error of that request, which
`suppress_process_exceptions` decides whether to raise. Until then the
cloud engines after it have no property metadata.

Each entry in the `warnings` list of an answer from the cloud service is
given as a warning, with any licence key masked.

See the [Start-up activity section of the cloud request engine specification](https://github.com/51Degrees/specifications/blob/main/pipeline-specification/pipeline-elements/cloud-request-engine.md#start-up-activity).

## Pointing the engine at another host

The engine calls `https://cloud.51degrees.com/api/v4/` unless told
otherwise. Set the `_51DEGREES_CLOUD_ENDPOINT` environment variable, or pass
`cloud_endpoint` in the engine settings, to the API base of another
host including the `/api/v4/` segment. `FOD_CLOUD_API_URL`, the old name
of that variable, is deprecated. The engine reads it only when
`_51DEGREES_CLOUD_ENDPOINT` is not set, and warns once that the old name
was used. `Constants.FOD_CLOUD_API_URL` is deprecated as well, and
`Constants.CLOUD_ENDPOINT` replaces it. A host other than
cloud.51degrees.com would be used to (a) use an on premise web server,
or (b) use a privately hosted version of the 51Degrees cloud for
performance reasons. This is the private hosting option of the cloud
service, and both run the same service, so code written against one
works unchanged against the other.

## Examples

The [examples](examples/readme.md) folder holds examples that use this
engine to get device detection and IP intelligence results from one request
to the 51Degrees cloud service, with a resource key or a licence key. Its
readme says how to run them.

## Engines that use it

It is used by the cloud versions of the following 51Degrees engines:

- [**fiftyone_devicedetection**](https://pypi.org/project/fiftyone-devicedetection/) - Get details about the devices accessing your web page
- [**fiftyone_location**](https://pypi.org/project/fiftyone-location/) - Get postal address details from the location of devices accessing your web page

## Find out more

- [Build your own](https://51degrees.com/build-your-own?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=find-out-more-build-your-own)
- [Pipeline API documentation](https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=find-out-more-documentation)
- [Pipeline API examples](https://51degrees.com/documentation/_pipeline_api__examples__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=find-out-more-examples)
- [Cloud service documentation](https://51degrees.com/documentation/_services__cloud__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine&utm_term=find-out-more-cloud-service)
- https://github.com/51Degrees/51degrees-python

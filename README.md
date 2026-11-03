# 51Degrees Python

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=51degrees-python "Data rewards the curious") **Python packages for the Pipeline API, Device Detection, IP Intelligence and Location**

This repository holds the 51Degrees Python packages published to PyPI. Each
product is in its own folder, which has its own README.

| Product | Folder | PyPI packages |
| --- | --- | --- |
| Pipeline API | [pipeline](pipeline/readme.md) | `fiftyone_pipeline_core`, `_engines`, `_engines_fiftyone`, `_cloudrequestengine`, `_translation`, `_did` |
| Device Detection | [device-detection](device-detection/readme.md) | `fiftyone_devicedetection`, `_shared`, `_cloud`, `_onpremise` |
| IP Intelligence | [ip-intelligence](ip-intelligence/readme.md) | `fiftyone_ipintelligence`, `_shared`, `_cloud`, `_onpremise`, `_translation` |
| Location | [location](location/readme.md) | `fiftyone_location` |

The packages and the order they depend on each other are listed in
[ci/packages.json](ci/packages.json).

## Getting the code

Clone with the submodules:

```
git clone --recurse-submodules https://github.com/51Degrees/51degrees-python.git
```

Each product's README says what else it needs, such as a C/C++ compiler for
the on-premise engines and the data files.

## Supported Python versions

The packages support Python 3.10 and later. The
[tested versions](https://51degrees.com/documentation/_info__tested_versions.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=tested-versions)
page lists the versions each release is tested against.

## Versions

Each package has its own version and is released only when it, or a package
it depends on, changes. A release is tagged `<package>/<version>`, for example
`fiftyone_pipeline_core/4.5.39`, and has its own GitHub release.

## History

This repository brings together the `pipeline-python`,
`device-detection-python`, `location-python` and `ip-intelligence-python`
repositories, each in a folder named without the language: `pipeline`,
`device-detection`, `location` and `ip-intelligence`. Their full history is included, with every commit keeping its original
SHA, so `git log --follow` traces a file back through the move. The tags and
releases of the original repositories stay with those repositories.

## Licence

[European Union Public Licence v1.2](LICENSE), which every package declares.

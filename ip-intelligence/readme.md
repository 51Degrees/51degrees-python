# 51Degrees IP Intelligence Engines

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=51degrees-ip-intelligence-engines "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/ip-intelligence-python/index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=51degrees-ip-intelligence-engines "developer documentation")

## Introduction

This repository contains the IP intelligence engines for the Python
implementation of the [51Degrees Pipeline API](https://51degrees.com/documentation/index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=introduction).

51Degrees IP Intelligence resolves an IP address to details about the
network it belongs to (registered name, owner and country) and, with
the Enterprise data file, the location associated with it.

The specification is also [available on GitHub](https://github.com/51Degrees/specifications)
and is recommended reading if you wish to understand the concepts and
design of this API.

## Dependencies

For runtime dependencies, see our
[dependencies](https://51degrees.com/documentation/_info__dependencies.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=dependencies)
page. The [tested versions](https://51degrees.com/documentation/_info__tested_versions.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=dependencies)
page shows the Python versions that we currently test against.

### Git submodules

The on-premise engine wraps the native
[51degrees-cxx](https://github.com/51Degrees/51degrees-cxx/blob/main/docs/ipi/README.md)
library, and the
[ip-intelligence-data](https://github.com/51Degrees/ip-intelligence-data)
repository (data and evidence files used for testing) is also included, both
as git submodules. When cloning, use:

```
git clone --recurse-submodules https://github.com/51Degrees/51degrees-python.git
```

or if you have already cloned:

```
git submodule update --init --recursive
```

### Data files

The on-premise engine requires a `.ipi` data file. The
[ip-intelligence-data](https://github.com/51Degrees/ip-intelligence-data)
submodule provides a freely available network-only data file
(`51Degrees-IPIV4AsnIpiV41.ipi`), which the examples tests and
`CommittedDataFileTests` use, along with the evidence files used for
testing. The on-premise unit tests default to
`assets/51Degrees-LiteIpiV41.ipi`.

For the full set of properties (location, registration, etc.) an enterprise
data file is required. To obtain one for testing, please
[contact us](https://51degrees.com/contact-us?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=readme.md&utm_term=data-files). Supply its path as a command
line argument to the examples, or place it within the project space.

Note: the engine reads exactly one data file format version, set by
`FIFTYONE_DEGREES_IPI_TARGET_VERSION_MAJOR` and `_MINOR` in the
`ip-intelligence-cxx` submodule's `src/ipi.c`, and refuses any other as
"an unsupported version". Move the `ip-intelligence-cxx` and
`ip-intelligence-data` pins together. `CommittedDataFileTests` in
[test_ipintelligence.py](fiftyone_ipintelligence_onpremise/tests/test_ipintelligence.py)
fails when the two disagree.

## Folders

- `fiftyone_ipintelligence` - umbrella package containing the
  `IpIntelligencePipelineBuilder` which builds cloud or on-premise
  pipelines depending on configuration.
- `fiftyone_ipintelligence_cloud` - the cloud engine, which consumes
  the 51Degrees cloud service.
- `fiftyone_ipintelligence_onpremise` - the on-premise engine, which
  wraps ip-intelligence-cxx via SWIG.
- `fiftyone_ipintelligence_shared` - code shared between the engines.
- `fiftyone_ipintelligence_examples` - usage examples for both engines.
- `ip-intelligence-data` - submodule containing the test data file and
  evidence files used by the examples and tests.

## Installation

### From PyPI

```
pip install fiftyone_ipintelligence
```

### From source

To build the on-premise native extension a C++17 compiler is required
(MSVC on Windows, GCC/Clang elsewhere).

```
pip install -e fiftyone_ipintelligence_shared
pip install -e fiftyone_ipintelligence_cloud
pip install -e fiftyone_ipintelligence_onpremise
pip install -e fiftyone_ipintelligence
pip install -e fiftyone_ipintelligence_examples
```

## Tests

Each package has its own test suite, run with pytest (or tox):

```
cd fiftyone_ipintelligence_cloud && python -m pytest tests
cd fiftyone_ipintelligence_onpremise && python -m pytest tests
cd fiftyone_ipintelligence_shared && python -m pytest tests
cd fiftyone_ipintelligence_examples && python -m pytest tests
```

- The cloud tests run against a mocked cloud service, so no resource
  key is required. Set the `resource_key` environment variable to also
  exercise the live cloud service.
- The on-premise tests require a data file (see Data files above). Set
  the `IPINTELLIGENCEDATAFILE` environment variable to use a data file
  from a custom location.

## Examples

See [fiftyone_ipintelligence_examples](fiftyone_ipintelligence_examples/readme.md)
for console and web examples for both the cloud and on-premise engines.

## License

This project is licensed under the
[European Union Public Licence v.1.2](LICENSE).

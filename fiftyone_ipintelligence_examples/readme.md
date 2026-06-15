# 51Degrees IP Intelligence Engines - Examples

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=repository&utm_content=readme_main&utm_campaign=python-open-source "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/ip-intelligence-python/index.html?utm_source=github&utm_medium=repository&utm_content=documentation&utm_campaign=python-open-source "developer documentation")

## Introduction

Usage examples for the 51Degrees IP intelligence engines.

## Cloud examples

Require a resource key in the `resource_key` environment variable.
Obtain one from the [51Degrees Configurator](https://configure.51degrees.com/).

- `cloud/gettingstarted_console.py` - resolve IP addresses using the
  cloud service from the console.
- `cloud/getallproperties_console.py` - resolve an IP address and list
  every property returned by the cloud service.
- `cloud/metadata_console.py` - list the properties and accepted evidence
  keys exposed by the cloud service.
- `cloud/gettingstarted_web/` - Flask web app using the cloud service.

```
python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_console
python -m fiftyone_ipintelligence_examples.cloud.getallproperties_console
python -m fiftyone_ipintelligence_examples.cloud.metadata_console
python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_web
```

## On-premise examples

Require a `.ipi` data file in the current (4.5) data format. The
`ip-intelligence-data` submodule includes a freely available network-only
file (`51Degrees-IPIV4AsnIpiV41.ipi`) that the examples fall back to; it
only contains the ASN/network properties, so location and registration
properties are reported as "not present in the data file".

For the full set of properties, use an enterprise data file - to obtain
one for testing please [contact us](https://51degrees.com/contact-us) - and
supply its path as the first command line argument. (The on-premise engine
must be built against an `ip-intelligence-cxx` revision targeting the 4.5
format; see the repository PROGRESS.md.)

- `onpremise/gettingstarted_console.py` - resolve IP addresses from the
  console using a local data file.
- `onpremise/metadata_console.py` - list the properties available from
  the data file.
- `onpremise/offlineprocessing.py` - batch process the evidence file
  from the ip-intelligence-data repository.
- `onpremise/performance_console.py` - benchmark the number of IP lookups
  performed per second.
- `onpremise/compare_console.py` - compare the location returned for each
  IP address against a CSV of known-true locations.
- `onpremise/datafileupdate_console.py` - demonstrate automatic data file
  updates (requires an enterprise license key).
- `onpremise/gettingstarted_web/` - Flask web app using the on-premise
  engine.

```
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.metadata_console [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.offlineprocessing [data-file [evidence-file]]
python -m fiftyone_ipintelligence_examples.onpremise.performance_console [-d data-file] [-e evidence-file]
python -m fiftyone_ipintelligence_examples.onpremise.compare_console [-d data-file] [-t truth-file]
python -m fiftyone_ipintelligence_examples.onpremise.datafileupdate_console <license-key> [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_web
```

Examples that are not ported from the .NET examples: `Metrics-Console`
(the on-premise engine's range enumeration API is not exposed through the
Python wrapper) and the `Mixed` examples (which combine device detection
and IP intelligence).

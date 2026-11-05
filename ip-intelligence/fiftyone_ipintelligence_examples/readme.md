# 51Degrees IP Intelligence Engines - Examples

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-readme.md&utm_term=51degrees-ip-intelligence-engines-examples "Data rewards the curious") **Python IP Intelligence**

[Developer Documentation](https://51degrees.com/documentation/_ip_intelligence__index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-readme.md&utm_term=51degrees-ip-intelligence-engines-examples "developer documentation")

## Introduction

Usage examples for the 51Degrees IP intelligence engines.

## Cloud examples

Require a resource key in the `resource_key` environment variable.
Obtain one from the [51Degrees Configurator](https://configure.51degrees.com/?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-readme.md&utm_term=cloud-examples).

- `cloud/gettingstarted_console.py` - resolve IP addresses using the
  cloud service from the console.
- `cloud/getallproperties_console.py` - resolve an IP address and list
  every property returned by the cloud service.
- `cloud/metadata_console.py` - list the properties and accepted evidence
  keys exposed by the cloud service.
- `cloud/mixed_console.py` - combine device detection and IP intelligence
  in a single cloud pipeline (requires the device detection package).
- `cloud/gettingstarted_web/` - Flask web app using the cloud service.

```
python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_console
python -m fiftyone_ipintelligence_examples.cloud.getallproperties_console
python -m fiftyone_ipintelligence_examples.cloud.metadata_console
python -m fiftyone_ipintelligence_examples.cloud.mixed_console
python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_web
```

## On-premise examples

Use a `.ipi` data file in the format the engine reads (see
[Data files](../readme.md#data-files)). The data repository, at
`cxx/data`, links to the two free data files, and an example downloads the
one it uses the first time it is missing, so the examples run from a fresh
clone with no settings. The free Lite data file (`51Degrees-LiteV41.ipi`)
has the registration properties, such as RegisteredName and
RegisteredCountry, and most examples use it. The free ASN data file
(`51Degrees-IPIV4AsnIpiV41.ipi`) has the ASN properties and is far smaller,
so the performance and data file update examples use it.

The location, range and connection properties are only in the Enterprise
data file. An example run on a free data file shows each property it lacks
as needing the Enterprise data file, and gives a link to
[contact us](https://51degrees.com/contact-us?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_examples-readme.md&utm_term=on-premise-examples) about a copy.
The countries and comparison examples need those properties throughout, so
on a free data file they say which they need and stop. Supply the path to
an Enterprise data file as the first command line argument, or with `-d`,
to see every property.

- `onpremise/gettingstarted_console.py` - resolve IP addresses from the
  console using a local data file.
- `onpremise/metadata_console.py` - list the properties available from
  the data file.
- `onpremise/countries_console.py` - list the countries an IP address is
  most likely in, with their names translated (needs the Enterprise data
  file).
- `onpremise/offlineprocessing.py` - batch process the evidence file
  from the data repository.
- `onpremise/performance_console.py` - benchmark the number of IP lookups
  performed per second.
- `onpremise/compare_console.py` - compare the location returned for each
  IP address against a CSV of known-true locations.
- `onpremise/datafileupdate_console.py` - demonstrate automatic data file
  updates (needs a licence key, and without one says where to ask for one).
- `onpremise/mixed_console.py` - combine device detection and IP
  intelligence in a single on-premise pipeline (requires the device
  detection package and a `.hash` data file).
- `onpremise/gettingstarted_web/` - Flask web app using the on-premise
  engine.

```
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.metadata_console [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.countries_console [data-file]
python -m fiftyone_ipintelligence_examples.onpremise.offlineprocessing [data-file [evidence-file]]
python -m fiftyone_ipintelligence_examples.onpremise.performance_console [-d data-file] [-e evidence-file]
python -m fiftyone_ipintelligence_examples.onpremise.compare_console [-d data-file] [-t truth-file]
python -m fiftyone_ipintelligence_examples.onpremise.datafileupdate_console [license-key [data-file]]
python -m fiftyone_ipintelligence_examples.onpremise.mixed_console [hash-file [ipi-file]]
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_web
```

The mixed examples combine device detection with IP intelligence and so
require the device detection package, installed via the `mixed` extra:

```
pip install -e fiftyone_ipintelligence_examples[mixed]
```

The only .NET example not ported is `Metrics-Console`, as the on-premise
engine's range enumeration API is not exposed through the Python wrapper.

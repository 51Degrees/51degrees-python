# Working in this repository

If you have been asked to get an example running, follow
[Run the examples](#run-the-examples). It gives every step in order, from a
fresh clone to the output. The sections after it are notes on what is not
obvious from the code, for changing it. Keep them short and current. The
layout and how to get the code are in the [README](README.md).

## Run the examples

Device Detection's on-premise `gettingstarted_console` is the quickest
example to show, because its data file is about 35 MB. IP Intelligence's
on-premise `gettingstarted_console` runs on the free Asn data file, which is
about 6 MB, and shows registration values once it is given the Lite file,
which is a download of about 230 MB. Run each command from the repository root
unless the step says otherwise.

The on-premise engines are C and C++ code that is compiled when the package is
installed. PyPI has only source distributions of
`fiftyone-devicedetection-onpremise` and `fiftyone-ipintelligence-onpremise`,
so a compiler is needed whether the packages come from PyPI or from this
checkout. The steps below build them from this checkout, as the product
READMEs do.

### Prerequisites

- Git.
- Python 3.10 or later, as the README says. CI tests 3.10 to 3.14 on Ubuntu,
  Windows and macOS (`ci/options.json`).
- A C11 and C++17 compiler. On Windows that is Visual Studio 2019 or later, or
  the [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/),
  with Platform Toolset `v142` and Windows SDK `10.0.18362.0` or later. On
  Linux the Device Detection README gives
  `sudo apt-get install g++ make libatomic1`.
- For the data files, `curl`, `gzip` and `md5sum` (`md5` on macOS) on Linux
  and macOS, where the examples download with the shell script, and Windows
  PowerShell 5.1 or PowerShell 7 on Windows, where they use the PowerShell
  script.
- Network access to GitHub, to PyPI for the packages the examples depend on,
  and to `distributor.51degrees.com` for the data files.

Clone the repository with its submodules.

```
git clone --recurse-submodules https://github.com/51Degrees/51degrees-python.git
cd 51degrees-python
```

In a clone made without `--recurse-submodules`, fetch the submodules.

```
git submodule update --init --recursive
```

### Data files

The examples use the free data files, which need no licence key. They are not
stored in this repository. The `cxx` submodule holds the
[data](https://github.com/51Degrees/data) repository as `cxx/data`, which has a
link to each file, and a script downloads them into `cxx/data/device-detection`
and `cxx/data/ip-intelligence`.

On Linux and macOS, run the shell script.

```
sh cxx/data/get-data-files.sh
```

On Windows, run the PowerShell script. Windows PowerShell can refuse to run a
script file under the policy Windows sets by default, so run it the way the
examples do.

```
powershell -NoProfile -ExecutionPolicy Bypass -File cxx/data/get-data-files.ps1
```

Where PowerShell 7 is installed, `pwsh cxx/data/get-data-files.ps1` does the
same on any system. Either script downloads every free file, the Asn file
included, and keeps a file that is already there. To download one file, give
its name, as in `sh cxx/data/get-data-files.sh 51Degrees-LiteV41.ipi`. An
example run with no argument downloads the file it needs itself, when the file
is missing.

#### Check the files

- `cxx/data/device-detection/51Degrees-LiteV4.1.hash` is more than 10 MB.
- `cxx/data/ip-intelligence/51Degrees-IPIV4AsnIpiV41.ipi` is more than 1 MB.
- `cxx/data/ip-intelligence/51Degrees-LiteV41.ipi` is more than 100 MB.

### Build

Install into a virtual environment, as CI does for the examples
(`device-detection/ci/run-integration-tests.ps1`). On Linux and macOS, make and
activate one with these commands.

```
python3 -m venv .venv
. .venv/bin/activate
```

On Windows, in PowerShell, run `python -m venv .venv` and then
`.venv\Scripts\Activate.ps1`.

Then install the Device Detection packages from source, with the commands the
Device Detection README gives, and the examples package. `setuptools` is
added because `python setup.py` needs it and Python 3.12 and later no longer
install it (`ip-intelligence/ci/setup-environment.ps1`).

```
cd device-detection
python -m pip install -r requirements.txt setuptools
python -m pip install -e fiftyone_devicedetection_shared/
python -m pip install -e fiftyone_devicedetection_cloud/
cd fiftyone_devicedetection_onpremise/
python setup.py build_clib build_ext
cd ../
python -m pip install -e fiftyone_devicedetection_onpremise/
python -m pip install -e fiftyone_devicedetection/
python -m pip install -e fiftyone_devicedetection_examples/
cd ..
```

Then install the IP Intelligence packages, with the commands the IP
Intelligence README gives.

```
cd ip-intelligence
pip install -e fiftyone_ipintelligence_shared
pip install -e fiftyone_ipintelligence_cloud
pip install -e fiftyone_ipintelligence_onpremise
pip install -e fiftyone_ipintelligence
pip install -e fiftyone_ipintelligence_examples
cd ..
```

The packages these need from elsewhere, such as the Pipeline API packages,
come from PyPI. CI installs the ones in `pipeline/` over them
(`ci/setup-environment.ps1`), which running an example does not need.

### Run

Run the Device Detection example from the repository root with no argument.
It looks for `cxx/data/device-detection/51Degrees-LiteV4.1.hash` in the folder
it runs in and each folder above it, and runs the download script when the
file is missing, with Windows PowerShell on Windows and `sh` on Linux and
macOS (`find_file` in
`device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py`).

```
python -m fiftyone_devicedetection_examples.onpremise.gettingstarted_console
```

The IP Intelligence example with no argument looks for the Asn file in the
folder it runs in and in its `assets` and `cxx/data/ip-intelligence` folders,
then does the same in each of the seven folders above it, and downloads the
file into `cxx/data/ip-intelligence` when it is missing. To see registration
values, download the Lite file first, as "Data files" says, and give its path
as the first argument.

```
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console cxx/data/ip-intelligence/51Degrees-LiteV41.ipi
```

Either example uses a path given as the first argument as it is, so a file
named that way is never downloaded.

### Correct output

When an example downloads its data file, it first prints
`<file> is missing, so it is being downloaded by running` and, on the next
line, the command, then the script's `Downloading` and `Saved` lines.

The pipeline logger writes through Python's `logging`, so its lines go to
standard error, each as `INFO:root:` or `WARNING:root:` followed by a
dictionary that holds the time, the level and the message.

The Device Detection example logs `Using a 'Lite' data file created '<date>'
from location '<path>'`, a warning that it is using the Lite file, and possibly
a warning that the file is more than 30 days old. Both warnings are expected.
Then for each of five sets of evidence it prints `Input values:` and the
evidence, then `Results:` with `Mobile Device`, `Platform Name`,
`Platform Version`, `Browser Name` and `Browser Version`. The first set is a
User-Agent from a Samsung Android phone.

The IP Intelligence example logs `Using a '<product>' data file created
'<date>'`, then for each of four IP addresses, starting with `116.154.188.222`,
prints `Input values:` with `query.client-ip`, then `Results:` with a line for
each of 16 properties, starting with `RegisteredName`, `RegisteredOwner` and
`RegisteredCountry`. A property the data file lacks reads
`This property is not present in the data file.` With the Asn file that is
every registration and location property, as the examples' README says. The
Lite file has RegisteredName, RegisteredOwner and RegisteredCountry, so with it
those three lines are read from the file.

The paid data files have many more properties, as the
[pricing page](https://51degrees.com/pricing?utm_source=github&utm_medium=docs&utm_campaign=51degrees-python&utm_content=agents.md&utm_term=correct-output)
describes.

### Cloud examples

The cloud examples need a resource key, which a person creates in the
configurator, so ask for one if none is set. A key with the properties the
Device Detection cloud example uses can be made
[here](https://configure.51degrees.com/1QWJwHxl?utm_source=github&utm_medium=docs&utm_campaign=51degrees-python&utm_content=agents.md&utm_term=cloud-examples),
which is the configuration the example's own message names, and a key for IP
Intelligence in the
[configurator](https://configure.51degrees.com/?utm_source=github&utm_medium=docs&utm_campaign=51degrees-python&utm_content=agents.md&utm_term=cloud-examples).

The Device Detection and IP Intelligence cloud examples take the key as
their first argument, or from `_51DEGREES_RESOURCE_KEY`.

```
_51DEGREES_RESOURCE_KEY=<key> python -m fiftyone_devicedetection_examples.cloud.gettingstarted_console
_51DEGREES_RESOURCE_KEY=<key> python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_console
```

In PowerShell, set `$env:_51DEGREES_RESOURCE_KEY = '<key>'` first. Without
a key, each
example logs an error that names the variable and the configurator.

### Pitfalls

- **A data file that is not there.** `cxx/data` holds a `.link` for each file
  rather than the file. An example run with no argument downloads a missing
  file, so it needs the network and the tools under "Prerequisites". Check
  the file sizes as above.
- **Running outside the repository, or without the submodules.** The Device
  Detection example then finds no `cxx/data`, searches for up to 5 seconds
  and, when it finds nothing, logs `Failed to find a device detection data
  file` with the advice to run `git submodule update --init --recursive`. Run
  it from the repository root, in a clone made with Git, because a zip
  download of the repository has no submodules.
- **No compiler, or no `setuptools`.** `python setup.py build_clib build_ext`
  and the on-premise installs compile C and C++, and on Python 3.12 and later
  `python setup.py` stops with `No module named 'setuptools'` until it is
  installed.
- **Long paths on Windows.** CI sets `TEMP` to `C:\tmp` on Windows to keep
  within the MSVC path length limit
  (`device-detection/ci/run-integration-tests.ps1`), so build from a short
  folder path.
- **Scripts blocked in Windows PowerShell.** Running `Activate.ps1`, like the
  Device Detection README's `setup.ps1`, needs PowerShell to allow scripts,
  which that README does with `Set-ExecutionPolicy -Scope CurrentUser Bypass`.
- **Pipenv.** The Device Detection README suggests `pipenv install`, but there
  is no `Pipfile` in the repository. Use the virtual environment above.
- **What CI does not test.** CI runs the examples' tests, which call each
  example's code rather than its `main`. The Device Detection tests use the
  Lite file that `device-detection/ci/fetch-assets.ps1` links in from CI's
  assets, and the IP Intelligence example tests use the Asn file and throw
  their output away.

## Products keep their own CI scripts

Each product folder still has the `ci/` scripts it had as its own repository,
and they know that product's packages, assets and test quirks. The scripts in
the root `ci/` are what common-ci calls. Each runs the same step of every
product a change affects, with the product's own script and the product folder
as `-RepoName` ([ci/dispatch.ps1](ci/dispatch.ps1)). So a change to how one
product is built or tested belongs in that product's `ci/`, not in the root.

A change touches a product when it is in that product's folder, or in a
package another product depends on; a change outside every product folder
touches all of them ([ci/packages.ps1](ci/packages.ps1),
`Resolve-AffectedProducts`).

## Versions are per package

Every package is versioned and tagged on its own, `<package>/<version>`. A
package is released when its folders changed since its last tag, or when a
package it depends on is released. The examples packages are tested but never
published. common-ci's publish carries one version; here it is only a label,
and the release plan in `ci/packages.ps1` decides what is built, published
and tagged. Never push a plain `4.5.x` tag: nothing here reads one.

`ci/packages.json` is the list of packages and what each depends on. Add a
package there, with a `FirstVersion` if it has never been released, or it is
never published.

## Pipeline packages come from this checkout

As separate repositories, device detection, IP intelligence and location
installed the pipeline packages from PyPI. In CI the root
`ci/setup-environment.ps1` installs them from `pipeline/` over those,
so a pipeline change is tested with every product in the same run.

A package's `setup.py` reads its version from a `version.txt`, which only
`pipeline/fiftyone_pipeline_did` commits, so any other package installed from
a checkout is 0.0.0. That is below the minimum versions of the pipeline
packages that the on-premise and examples packages require, so
`ci/write-package-versions.ps1` gives each published package the version this
commit would release it at. The root `ci/setup-environment.ps1` runs it
first. Run `pwsh ci/write-package-versions.ps1` before running those
packages' tests from a checkout.

## Submodules

The C/C++ engines are the `cxx` submodule, listed in the root `.gitmodules`.
The data files come through cxx's own `data` submodule, at
`cxx/data/device-detection` and `cxx/data/ip-intelligence`, where each free
file is a `<file>.link` that `cxx/data/get-data-files.ps1` or
`cxx/data/get-data-files.sh` downloads. Each product's `ci/fetch-assets.ps1`
gets the files its tests need, and the examples' `example_utils.py` runs the
script for a file that is missing. The IP Intelligence on-premise package must
compile its own copy of the common C library with large data file support;
the Device Detection one without it.

A package's `ExtraPaths` in `ci/packages.json` cannot be a folder inside
`cxx`, because git reports any change there as a change to `cxx` itself. A
cxx update therefore releases no package, even when it brings new translations
in `cxx/data/ip-intelligence`.

## Releases

Pull requests go to `rc`, not `main`, and stay drafts until they have been
reviewed, because the nightly merges any pull request into `rc` that is not a
draft and has no review requested. When a release is wanted, one pull request
merges `rc` into `main`, and the "Only rc into main" check fails a pull request
into `main` from any other branch.

## Releases

Pull requests go to `rc`, not `main`, and stay drafts until they have been
reviewed, because the nightly merges any pull request into `rc` that is not a
draft and has no review requested. When a release is wanted, one pull request
merges `rc` into `main`, and the "Only rc into main" check fails a pull request
into `main` from any other branch.

## History

The four repositories were brought in with `git subtree add`, so commit SHAs
match the originals. Use `git log --follow` to trace a file back through the
import.

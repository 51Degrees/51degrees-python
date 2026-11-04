# Working in this repository

If you have been asked to get an example running, follow
[Run the examples](#run-the-examples). It gives every step in order, from a
fresh clone to the output. The sections after it are notes on what is not
obvious from the code, for changing it. Keep them short and current. The
layout and how to get the code are in the [README](README.md).

## Run the examples

Device Detection's on-premise `gettingstarted_console` is the quickest
example to show, because its data file is about 35 MB. IP Intelligence's
on-premise `gettingstarted_console` runs with no download at all, on the Asn
data file committed to its data submodule, and shows registration values once
it is given the Lite file, which is a download of about 230 MB. Run each
command from the repository root unless the step says otherwise.

The on-premise engines are C and C++ code that is compiled when the package is
installed. PyPI has only source distributions of
`fiftyone-devicedetection-onpremise` and `fiftyone-ipintelligence-onpremise`,
so a compiler is needed whether the packages come from PyPI or from this
checkout. The steps below build them from this checkout, as the product
READMEs do.

### Prerequisites

- Git, and [Git LFS](https://git-lfs.github.com/) for the Device Detection
  data file.
- Python 3.10 or later, as the README says. CI tests 3.10 to 3.14 on Ubuntu,
  Windows and macOS (`ci/options.json`).
- A C11 and C++17 compiler. On Windows that is Visual Studio 2019 or later, or
  the [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/),
  with Platform Toolset `v142` and Windows SDK `10.0.18362.0` or later. On
  Linux the Device Detection README gives
  `sudo apt-get install g++ make libatomic1`.
- For the IP Intelligence Lite file, PowerShell 7 (`pwsh`) on any system, or
  `curl`, `gunzip` and `md5sum` (`md5` on macOS) for the shell script on Linux
  and macOS.
- Network access to GitHub, and to PyPI for the packages the examples depend
  on.

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

The examples use free data files, which need no licence key. Two layouts
exist. Read the "Getting the code" section of `README.md` in your checkout to
find out which one applies.

- **The section gives no command for the data files.** This is the layout on
  `rc` and `main` today. The Device Detection files are in
  `cxx/device-detection-data`. The IP Intelligence files are in this
  repository's own `ip-intelligence/ip-intelligence-data` submodule, and in
  `cxx/ip-intelligence-data`, both at the same commit. Follow
  "Without cxx/data".
- **The section gives `sh cxx/data/get-data-files.sh`.** The draft pull request
  [#28](https://github.com/51Degrees/51degrees-python/pull/28) moves the
  examples and tests to the [data](https://github.com/51Degrees/data)
  repository, which cxx carries as `cxx/data`, and removes
  `ip-intelligence/ip-intelligence-data`. Once it is merged, follow
  "With cxx/data".

Go by the README rather than by whether `cxx/data` exists, because the folder
can arrive with a newer `cxx` before the examples here read it.

#### Without cxx/data

The Device Detection Lite file is stored with Git LFS. Install Git LFS, for
example with `sudo apt-get install git-lfs` on Ubuntu, then pull the file in
its submodule. The Device Detection README names an older path for this
folder, `src/fiftyone_devicedetection_onpremise/cxx/device-detection-data`,
which no longer exists.

```
git lfs install
cd cxx/device-detection-data
git lfs pull
cd ../..
```

The IP Intelligence Asn file, `51Degrees-IPIV4AsnIpiV41.ipi`, is committed, so
it needs no download. A script in the IP Intelligence data submodule downloads
the Lite file. Run it from inside that folder, because it saves the file in
the folder it runs from.

```
cd ip-intelligence/ip-intelligence-data
pwsh ./get-lite-file-from-azure.ps1
cd ../..
```

On Linux and macOS, `./get-lite-file-from-azure.sh` in the same folder does
the same. Either script also downloads the Asn file over the committed copy,
so `git status` then shows the submodule as modified, which is expected.

#### With cxx/data

```
sh cxx/data/get-data-files.sh
```

In PowerShell, run `./cxx/data/get-data-files.ps1` instead. Either script
downloads every free file into `cxx/data/device-detection` and
`cxx/data/ip-intelligence`, the Asn file included, and keeps a file that is
already there. In this layout an example whose file is missing runs the
script for that file itself.

#### Check the files

- `cxx/device-detection-data/51Degrees-LiteV4.1.hash` is more than 10 MB. A
  file of about 130 bytes that starts with
  `version https://git-lfs.github.com/spec/v1` is a Git LFS pointer, which
  means Git LFS has not pulled the file.
- `ip-intelligence/ip-intelligence-data/51Degrees-LiteV41.ipi`, if you
  downloaded it, is more than 100 MB.

With `cxx/data`, the files are in `cxx/data/device-detection` and
`cxx/data/ip-intelligence`.

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

Give the Device Detection example its data file as the first argument. Without
one it searches the folder it runs in, every folder below it and then each
folder above it, and gives up after 5 seconds (`find_file` in
`device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py`),
which a search of the whole repository can take.

```
python -m fiftyone_devicedetection_examples.onpremise.gettingstarted_console cxx/device-detection-data/51Degrees-LiteV4.1.hash
```

The IP Intelligence example takes a data file as its first argument too, as
its README says. Without one it looks for the Asn file in `.`, `assets`,
`ip-intelligence-data` and `cxx/ip-intelligence-data` below the folder it runs
in and each of the seven folders above it, so from the repository root it
finds `cxx/ip-intelligence-data/51Degrees-IPIV4AsnIpiV41.ipi`.

```
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console
python -m fiftyone_ipintelligence_examples.onpremise.gettingstarted_console ip-intelligence/ip-intelligence-data/51Degrees-LiteV41.ipi
```

With `cxx/data`, the paths are
`cxx/data/device-detection/51Degrees-LiteV4.1.hash` and
`cxx/data/ip-intelligence/51Degrees-LiteV41.ipi`.

### Correct output

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

The Device Detection cloud example takes the key as its first argument, or
from `_51DEGREES_RESOURCE_KEY`, or from the older name `resource_key`, which
the Device Detection README uses. The IP Intelligence cloud example takes it
as its first argument or from `resource_key`.

```
resource_key=<key> python -m fiftyone_devicedetection_examples.cloud.gettingstarted_console
resource_key=<key> python -m fiftyone_ipintelligence_examples.cloud.gettingstarted_console
```

In PowerShell, set `$env:resource_key = '<key>'` first. Without a key, each
example logs an error that names the variable and the configurator.

### Pitfalls

- **A Git LFS pointer instead of the data file.** The engine cannot load it,
  so the Device Detection example stops before it prints any results. Check
  the file sizes as above.
- **The search for the data file.** Without an argument the Device Detection
  example can give up after 5 seconds and log `Failed to find a device
  detection data file`, so give it the path.
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
- **Windows line endings.** Git for Windows usually checks files out with
  `core.autocrlf=true`, and `ip-intelligence/ip-intelligence-data` has no
  `.gitattributes`, so its shell script gets Windows line endings and the
  shell cannot run it. Use the PowerShell script on Windows.
- **What CI does not test.** CI runs the examples' tests, which call each
  example's code rather than its `main`. The Device Detection tests find the
  Lite file that `device-detection/ci/fetch-assets.ps1` links into the
  examples package, and the IP Intelligence example tests use the Asn file and
  throw their output away.

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

## Submodules

The C/C++ engines and the data files are submodules, listed in the root
`.gitmodules` at their paths under each product folder. The IP Intelligence
on-premise package must compile its own copy of the common C library with
large data file support; the Device Detection one without it.

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

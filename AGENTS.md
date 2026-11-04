# Working in this repository

Notes on what is not obvious from the code. Keep them short and current. The
layout and how to get the code are in the [README](README.md).

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

## History

The four repositories were brought in with `git subtree add`, so commit SHAs
match the originals. Use `git log --follow` to trace a file back through the
import.

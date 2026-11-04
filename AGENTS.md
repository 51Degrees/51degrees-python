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

A package's `setup.py` reads its version from a `version.txt`, which only
`pipeline/fiftyone_pipeline_did` commits, so any other package installed from
a checkout is 0.0.0. That is below the minimum versions of the pipeline
packages that the on-premise and examples packages require, so
`ci/write-package-versions.ps1` gives each published package the version this
commit would release it at. The root `ci/setup-environment.ps1` runs it
first. Run `pwsh ci/write-package-versions.ps1` before running those
packages' tests from a checkout.

## Submodules

The C/C++ engines and the data files are submodules, listed in the root
`.gitmodules` at their paths under each product folder. The IP Intelligence
on-premise package must compile its own copy of the common C library with
large data file support; the Device Detection one without it.

## History

The four repositories were brought in with `git subtree add`, so commit SHAs
match the originals. Use `git log --follow` to trace a file back through the
import.

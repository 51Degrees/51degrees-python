param (
    [Parameter(Mandatory)][string]$RepoName,
    [Parameter(Mandatory)][string]$LanguageVersion
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

# PreBuild is a job of the publish workflow that needs no environment, as in
# each product's own script.
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping environment setup"
    exit 0
}

# Before anything installs a package from this checkout, so that each one
# installs at the version this commit would release it at.
& (Join-Path $PSScriptRoot 'write-package-versions.ps1') -RepoName $RepoName

Invoke-ProductStep 'setup-environment' $RepoName $PSBoundParameters

# The device detection, IP intelligence and location scripts install the
# pipeline packages from PyPI, because as separate repositories that was the
# only place to get them. Here the pipeline packages are in this checkout, so
# install those over the PyPI ones: a change to pipeline is then tested with
# the products that use it, in the same run, which is why the products were
# brought into one repository. fiftyone_pipeline_did is left out because no
# product depends on it and it needs its OWID copy before it builds.
$pipeline = 'fiftyone_pipeline_core', 'fiftyone_pipeline_engines',
    'fiftyone_pipeline_engines_fiftyone', 'fiftyone_pipeline_cloudrequestengine',
    'fiftyone_pipeline_translation'
$paths = $pipeline | ForEach-Object {
    Join-Path $RepoName 'pipeline' $_
}
pip install @paths || $(throw "pip install of the local pipeline packages failed")

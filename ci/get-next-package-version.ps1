param (
    [Parameter(Mandatory)][string]$RepoName,
    [Parameter(Mandatory)][string]$VariableName
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# common-ci's publish carries one version through its jobs. This repository
# releases each package at its own version (see packages.ps1), so that one
# version is only a label for the run: the highest version this publish
# releases. Whether anything is released is decided by
# package-update-required.ps1, and each package's version and tag by
# build-package.ps1 and publish-package.ps1, all from the same release plan.
$plan = @(Get-ReleasePlan $RepoName)
if ($plan.Count -gt 0) {
    $label = ($plan.Version | Sort-Object { [version]$_ })[-1]
} else {
    # Nothing to release. Any valid version will do, because
    # package-update-required.ps1 stops the publish before it is used.
    $label = '4.5.0'
}

Set-Variable -Scope Global -Name $VariableName -Value $label

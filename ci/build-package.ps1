param (
    [Parameter(Mandatory)][string]$RepoName,
    [string]$Version
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# Builds the packages this publish releases, each at its own version from the
# release plan. When nothing is to be released, every package is built at its
# released version, so that the tests have packages to install and the nightly
# publish passes without publishing anything. $Version is common-ci's label for
# the run and is not used.

$plan = @(Get-BuildPlan $RepoName)

# fiftyone_pipeline_did carries the OWID source inside itself, copied in by the
# pipeline product's script; see pipeline/ci/copy-owid-source.ps1.
if (($plan.Name -contains 'fiftyone_pipeline_did') -eq $true) {
    $pipeline = Join-Path $RepoName 'pipeline'
    & (Join-Path $pipeline 'ci' 'copy-owid-source.ps1') -RepoRoot $pipeline
}

# Packages with a C/C++ extension are published as source only, because PyPI
# rejects the wheel built here, which is tagged for this machine. They are
# marked SourceOnly in packages.json.
$sourceOnly = @(Get-Packages $RepoName |
    Where-Object { $_.SourceOnly -eq $true } | ForEach-Object { $_.Path })

foreach ($release in $plan) {
    Write-Output "::group::Build $($release.Name) $($release.Version)"
    ./python/build-package-pypi.ps1 -RepoName $RepoName `
        -Version $release.Version -Packages $release.Path `
        -SourceOnlyPackages $sourceOnly
    if ($LASTEXITCODE -ne 0) {
        throw "Building $($release.Name) failed"
    }
    Write-Output "::endgroup::"
}

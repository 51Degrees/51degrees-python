param (
    [Parameter(Mandatory)][string]$RepoName,
    [string]$Version
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# Called by common-ci's publish in place of its own check, because a plain tag
# lookup cannot tell this repository's packages apart. Exits 0 when the release
# plan has something in it and 1 when it is empty, as common-ci's check does.
# $Version is common-ci's label for the run and is not used here.

$plan = @(Get-ReleasePlan $RepoName)
if ($plan.Count -eq 0) {
    Write-Output "No package changed since its last release, so there is nothing to publish"
    exit 1
}

Write-Output "This publish releases:"
$plan | Format-Table Name, Previous, Version, Reason -AutoSize | Out-String |
    Write-Output

# Each package is held to its own release history, so a mistaken minor move or
# a 0.x first release of any one package stops the whole publish before
# anything is built. check-version-bump.ps1 writes the reason.
foreach ($release in $plan) {
    ./steps/check-version-bump.ps1 -Version $release.Version `
        -RepoName $RepoName -TagPrefix $release.Name
    if ($LASTEXITCODE -ne 0) {
        throw "The version of $($release.Name) was refused, so nothing is published"
    }
}

exit 0

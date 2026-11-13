param (
    # common-ci's prefetch_assets action calls this script directly, not
    # through steps/run-script.ps1, and passes only the keys, so the name of
    # this repository's folder is the default. It is relative to the
    # common-ci checkout, which is where both callers run it from.
    [string]$RepoName = (Split-Path -Leaf (Split-Path -Parent $PSScriptRoot)),
    [string]$DeviceDetection,
    [string]$DeviceDetectionUrl,
    [string]$CsvUrl,
    [string]$IpIntelligence,
    [string]$IpIntelligenceUrl,
    # The branch a pull request merges into, which its changes are measured
    # against.
    [string]$Branch = 'main'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

# The prefetch in the Configure job fills the asset cache that every run that
# day restores, whatever it changes, so it fetches for every product.
$fetchProducts = $null
if ($env:GITHUB_JOB -eq 'Configure') {
    $fetchProducts = @((Get-Packages $RepoName).Product | Select-Object -Unique)
}
Invoke-ProductStep 'fetch-assets' $RepoName $PSBoundParameters $fetchProducts

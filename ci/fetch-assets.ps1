param (
    [Parameter(Mandatory)][string]$RepoName,
    [string]$DeviceDetection,
    [string]$DeviceDetectionUrl,
    [string]$CsvUrl,
    [string]$IpIntelligence,
    [string]$IpIntelligenceUrl
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'fetch-assets' $RepoName $PSBoundParameters

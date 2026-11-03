param (
    [Parameter(Mandatory)][string]$RepoName,
    [string]$Name,
    [bool]$RunPerformance
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'run-performance-tests' $RepoName $PSBoundParameters

param (
    [Parameter(Mandatory)][string]$RepoName,
    [string]$Name,
    [bool]$RunPerformance,
    # The branch a pull request merges into, which its changes are measured
    # against.
    [string]$Branch = 'main'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'run-performance-tests' $RepoName $PSBoundParameters

param (
    [Parameter(Mandatory)][string]$RepoName,
    # The branch a pull request merges into, which its changes are measured
    # against.
    [string]$Branch = 'main'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'run-unit-tests' $RepoName $PSBoundParameters

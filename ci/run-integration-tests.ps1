param (
    [Parameter(Mandatory)][string]$RepoName,
    [Parameter(Mandatory)][hashtable]$Keys,
    # The branch a pull request merges into, which its changes are measured
    # against.
    [string]$Branch = 'main',
    # False, from select-options.ps1, on every entry of a pull request but
    # one, so the browser contract runs once.
    [bool]$SeleniumContract = $true
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'run-integration-tests' $RepoName $PSBoundParameters

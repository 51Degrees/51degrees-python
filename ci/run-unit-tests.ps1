param (
    [Parameter(Mandatory)][string]$RepoName
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'run-unit-tests' $RepoName $PSBoundParameters

param (
    [Parameter(Mandatory)][string]$RepoName
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')

Invoke-ProductStep 'build-project' $RepoName $PSBoundParameters

param (
    [Parameter(Mandatory)][string]$RepoName
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'dispatch.ps1')
. (Join-Path $PSScriptRoot 'packages.ps1')

# Each package's tests take the packages it depends on from this checkout, so
# they test the code those packages are released with. A tox.ini that takes
# one from PyPI instead stops the tests before they run.
$gaps = @(Get-ToxGaps (Split-Path $PSScriptRoot))
if ($gaps.Count -gt 0) {
    throw "A tox.ini takes a package from PyPI that this checkout has:`n" +
        ($gaps -join "`n")
}

Invoke-ProductStep 'run-unit-tests' $RepoName $PSBoundParameters

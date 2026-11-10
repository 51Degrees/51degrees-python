# Every 51Degrees environment variable name in this repository starts with an
# underscore, because a POSIX shell cannot set a name that starts with a digit.
# This reads every file git tracks, which leaves out build output and the
# submodules, and fails on any name that starts with the digit.

[CmdletBinding()]
param(
    # The root of the checkout to read. The default is the repository this
    # script lives in.
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The start of a name a shell cannot set, split so this file does not match
# itself.
$digitInitial = '5' + '1DEGREES_'

# A name is not matched when a name character comes before it, so a name with
# a leading underscore is left alone.
$pattern = "(?<![A-Za-z0-9_])$digitInitial[A-Za-z0-9_]*"

$root = (Resolve-Path $RepoRoot).Path
$tracked = & git -C $root ls-files
if ($LASTEXITCODE -ne 0) {
    throw "git ls-files failed in $root"
}

$found = @()
foreach ($relative in $tracked) {
    $path = Join-Path $root $relative
    # A submodule is tracked as a directory, and its files belong to another
    # repository.
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $lineNumber = 0
    foreach ($line in [IO.File]::ReadLines($path)) {
        $lineNumber++
        foreach ($match in [regex]::Matches($line, $pattern)) {
            $found += "${relative}:${lineNumber}: $($match.Value)"
        }
    }
}

if ($found.Count -gt 0) {
    Write-Output $found
    throw ("$($found.Count) names start with a digit, which a POSIX shell " +
        'cannot set, so each must start with an underscore.')
}

Write-Output "No tracked file names a variable starting with a digit. $($tracked.Count) paths read."

# Every 51Degrees environment variable name in this repository starts with an
# underscore, because a POSIX shell cannot set a name that starts with a digit,
# and each variable has one name with nothing read in its place. This reads
# every file git tracks, which leaves out build output and the submodules, and
# fails on any name that starts with the digit and on any fallback name.
#
# The digit-initial names are matched in any case. The fallback names are
# matched with case, because the lower case resource_key and license_key are
# still the one name some examples and tests read, so ignoring case would fail
# on names that are not fallbacks.

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
$pattern = [regex]::new("(?<![A-Za-z0-9_])$digitInitial[A-Za-z0-9_]*",
    [Text.RegularExpressions.RegexOptions]::IgnoreCase)

# A bare RESOURCE_KEY or LICENSE_KEY read or set as an environment variable or
# held in a string by itself, or a constant holding a legacy name to fall back
# to. Only those are matched, so placeholder text such as YOUR_RESOURCE_KEY,
# and longer names that end in the same words, are left alone.
$fallback = [regex]::new(
    '(?:environ(?:\.get)?\s*[\(\[]\s*[''"]|getenv\(\s*[''"]|\$env:|' +
    'SetEnvironmentVariable\(\s*[''"])' +
    '(?:RESOURCE_KEY|LICENSE_KEY)(?![A-Za-z0-9_])|' +
    '[''"](?:RESOURCE_KEY|LICENSE_KEY)[''"]|' +
    '\bLEGACY_[A-Z_]*ENV_VARS?\b')

$root = (Resolve-Path $RepoRoot).Path
# Paths are listed as they are, so a path holding a non-ASCII character is not
# quoted and is still found.
$tracked = & git -C $root -c core.quotePath=false ls-files
if ($LASTEXITCODE -ne 0) {
    throw "git ls-files failed in $root"
}

$found = @()
$fallbacks = @()
$read = 0
$skipped = @()
foreach ($relative in $tracked) {
    $path = Join-Path $root $relative
    # A submodule is tracked as a directory, and its files belong to another
    # repository.
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $skipped += $relative
        continue
    }
    $read++
    $lineNumber = 0
    foreach ($line in [IO.File]::ReadLines($path)) {
        $lineNumber++
        foreach ($match in $pattern.Matches($line)) {
            $found += "${relative}:${lineNumber}: $($match.Value)"
        }
        foreach ($match in $fallback.Matches($line)) {
            $fallbacks += "${relative}:${lineNumber}: $($match.Value)"
        }
    }
}

Write-Output "$read paths read, $($skipped.Count) skipped as not files: $($skipped -join ', ')"

if ($found.Count -gt 0 -or $fallbacks.Count -gt 0) {
    Write-Output $found
    Write-Output $fallbacks
    throw ("$($found.Count) names start with a digit, which a POSIX shell " +
        'cannot set, so each must start with an underscore, and ' +
        "$($fallbacks.Count) fallback names are read, set or kept, where " +
        'each variable has one name.')
}

Write-Output 'No tracked file names a variable starting with a digit or a fallback name.'

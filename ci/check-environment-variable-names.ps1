# Every 51Degrees environment variable name in this repository starts with an
# underscore, because a POSIX shell cannot set a name that starts with a digit,
# and each variable has one name with nothing read in its place. This reads
# every file git tracks, which leaves out build output and the submodules, and
# fails on any name that starts with the digit and on any fallback name.
#
# Names are matched in any case, because Windows reads an environment
# variable name in any case, so a lower case old name is still the old name
# there.
#
# Dot-sourcing the script defines Find-EnvironmentNameProblem without reading
# the repository, which is how its tests use it.

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
$script:DigitInitialPattern = [regex]::new(
    "(?<![A-Za-z0-9_])$digitInitial[A-Za-z0-9_]*",
    [Text.RegularExpressions.RegexOptions]::IgnoreCase)

# An old name read or set as an environment variable, or given as a second
# name after a _51DEGREES_ one, or a constant holding a legacy name to fall
# back to. Only those are matched, so the builder setting resource_key or
# cloud_endpoint, placeholder text such as YOUR_RESOURCE_KEY, and longer names
# that end in the same words, are left alone. cloud_endpoint in particular is
# a pipeline setting as well as an old environment variable name, and only the
# environment variable moves.
#
# Two kinds of old name. FOD_CLOUD_API_URL, IPINTELLIGENCEDATAFILE,
# cloud_request_origin, ipintelligencetestkey and run_performance_tests are
# never anything but an environment variable, so they are matched wherever
# they appear. RESOURCE_KEY, LICENSE_KEY and cloud_endpoint also name things
# that are not environment variables, being pipeline settings, builder
# parameters and the fake resource key the cloud request engine's tests send,
# so those three are matched only where the line reads or sets a variable, or
# names one in a constant whose own name says so.
$plainOld = '(?:FOD_CLOUD_API_URL|IPINTELLIGENCEDATAFILE|cloud_request_origin|' +
    'ipintelligencetestkey|run_performance_tests)'
$sharedOld = '(?:RESOURCE_KEY|LICENSE_KEY|cloud_endpoint)'
$script:FallbackPattern = [regex]::new(
    "(?<![A-Za-z0-9_])$plainOld(?![A-Za-z0-9_])|" +
    '(?:environ(?:\.get|\.pop|\.setdefault)?\s*[\(\[]\s*|getenv\(\s*|' +
    "SetEnvironmentVariable\(\s*)['`"]$sharedOld['`"]|" +
    "\`$env:$sharedOld(?![A-Za-z0-9_])|" +
    "['`"]$sharedOld['`"]\s+in\s+os\.environ|" +
    "['`"]_51DEGREES_[A-Za-z0-9_]*['`"]\s*,\s*['`"]$sharedOld['`"]|" +
    # A constant whose own name says it holds a variable name, which is how
    # the cloud request engine and the example helpers name the one they then
    # read. A fixture value such as resourceKey = "resource_key" is left
    # alone, because that name goes on the wire and not in the environment.
    "[A-Za-z_][A-Za-z0-9_]*(?:ENV_VAR|ENVIRONMENT_VARIABLE|_VARIABLE)" +
    "[A-Za-z0-9_]*\s*=\s*['`"]$sharedOld['`"]|" +
    '\bLEGACY_[A-Z_]*ENV_VARS?\b',
    [Text.RegularExpressions.RegexOptions]::IgnoreCase)

# The problems on one line, each as its kind, 'digit' or 'fallback', and the
# text matched.
function Find-EnvironmentNameProblem([string]$Line) {
    foreach ($match in $script:DigitInitialPattern.Matches($Line)) {
        [pscustomobject]@{ Kind = 'digit'; Value = $match.Value }
    }
    foreach ($match in $script:FallbackPattern.Matches($Line)) {
        [pscustomobject]@{ Kind = 'fallback'; Value = $match.Value }
    }
}

if ($MyInvocation.InvocationName -eq '.') {
    return
}

$root = (Resolve-Path $RepoRoot).Path
# Paths are listed as they are, so a path holding a non-ASCII character is not
# quoted and is still found.
$tracked = & git -C $root -c core.quotePath=false ls-files
if ($LASTEXITCODE -ne 0) {
    throw "git ls-files failed in $root"
}

# The tests of this script name every form it fails on, on purpose.
$ownTests = 'ci/check-environment-variable-names.Tests.ps1'

$found = @()
$fallbacks = @()
$read = 0
$skipped = @()
foreach ($relative in $tracked) {
    if ($relative -eq $ownTests) {
        continue
    }
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
        foreach ($problem in Find-EnvironmentNameProblem $line) {
            $text = "${relative}:${lineNumber}: $($problem.Value)"
            if ($problem.Kind -eq 'digit') {
                $found += $text
            } else {
                $fallbacks += $text
            }
        }
    }
}

Write-Output ("$read paths read, $($skipped.Count) skipped as not files: " +
    "$($skipped -join ', '), and $ownTests left out")

if ($found.Count -gt 0 -or $fallbacks.Count -gt 0) {
    Write-Output $found
    Write-Output $fallbacks
    throw ("$($found.Count) names start with a digit, which a POSIX shell " +
        'cannot set, so each must start with an underscore, and ' +
        "$($fallbacks.Count) fallback names are read, set or kept, where " +
        'each variable has one name.')
}

Write-Output 'No tracked file names a variable starting with a digit or a fallback name.'

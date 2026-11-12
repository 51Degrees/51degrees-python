# Every 51Degrees environment variable name in this repository starts with an
# underscore, because a POSIX shell cannot set a name that starts with a digit,
# and everything documents that one name. This reads every file git tracks,
# which leaves out build output and the submodules, and fails on any name
# that starts with the digit and on any old name.
#
# A variable whose name changed is still read under its old name when the new
# one is not set, which is deprecated. So an old name is left alone in the two
# places that read happens. One is a line where the old name is the argument
# straight after its _51DEGREES_ name, which is how each deprecated read is
# written. The other is the files $FallbackPaths lists, which hold the
# deprecated constants, the tests that set an old name to check the read, and
# the lists of names tox passes to the tests.
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

# An old name read or set as an environment variable, or a constant holding
# one. Only those are matched, so the builder setting resource_key or
# cloud_endpoint, placeholder text such as YOUR_RESOURCE_KEY, and longer names
# that end in the same words, are left alone. cloud_endpoint in particular is
# a pipeline setting as well as an old environment variable name, and only the
# environment variable moves.
#
# Two kinds of old name. The old cloud endpoint name, the old IP Intelligence
# data file name, the name the shared key helper's test set and the name that
# turned the performance examples on are never anything but an environment
# variable, so they are matched wherever they appear. Each is built from two
# pieces below so that this file does not name one itself.
#
# Those four, the ones $plainOld holds, keep their case, unlike every other
# pattern here, because the IP Intelligence data file's old name differs from
# the class name IpIntelligenceDataFile by case alone, and a class is not a
# variable.
#
# RESOURCE_KEY, LICENSE_KEY, cloud_endpoint and cloud_request_origin also name
# things that are not environment variables, being pipeline settings, builder
# parameters and the fake resource key the cloud request engine's tests send,
# so those four, the ones $sharedOld holds, are matched only where the line
# reads or sets a variable, or names one in a constant whose own name says so.
# They are matched in any case, because the line having to read or set a
# variable is what keeps a settings name out.
$plainOld = '(?-i:FOD_CLOUD' + '_API_URL|IPINTELLIGENCE' + 'DATAFILE|' +
    'ipintelligence' + 'testkey|run_performance' + '_tests)'
$sharedOld = '(?:RESOURCE_KEY|LICENSE_KEY|cloud_endpoint|cloud_request_origin)'
$script:FallbackPattern = [regex]::new(
    "(?<![A-Za-z0-9_])$plainOld(?![A-Za-z0-9_])|" +
    '(?:environ(?:\.get|\.pop|\.setdefault)?\s*[\(\[]\s*|getenv\(\s*|' +
    "SetEnvironmentVariable\(\s*)['`"]$sharedOld['`"]|" +
    # The env token on its own, with a following backslash allowed, rather
    # than next to a dollar sign, because PowerShell braces a name as well as
    # prefixing it and reads one through the Env: drive, and a workflow
    # expression braces one too.
    "env[:.]\\?$sharedOld(?![A-Za-z0-9_])|" +
    "['`"]$sharedOld['`"]\s+in\s+os\.environ|" +
    # A constant whose own name says it holds a variable name, which is how
    # the cloud request engine and the example helpers name the one they then
    # read. A fixture value such as resourceKey = "resource_key" is left
    # alone, because that name goes on the wire and not in the environment.
    "[A-Za-z_][A-Za-z0-9_]*(?:ENV_VAR|ENVIRONMENT_VARIABLE|_VARIABLE)" +
    "[A-Za-z0-9_]*\s*=\s*['`"]$sharedOld['`"]",
    [Text.RegularExpressions.RegexOptions]::IgnoreCase)

# A name given as the argument straight after a _51DEGREES_ name, which is how
# a deprecated read of an old name is written. The old name is taken out of
# the line before the line is checked.
$script:DeprecatedReadPattern = [regex]::new(
    "(['`"]_51DEGREES_[A-Za-z0-9_]*['`"]\s*,\s*)['`"][A-Za-z0-9_]+['`"]")

# The files that may name an old variable anywhere, each as a pattern its
# path from the root of the repository matches. They hold the deprecated
# constants, the documentation and comments that say an old name is still
# read, the tests that set an old name to check it is read, and the lists of
# names tox passes to the tests.
$script:FallbackPaths = @(
    '(^|/)tox\.ini$'
    '(^|/)example_utils\.py$'
    '(^|/)test_environment_names\.py$'
    '^pipeline/fiftyone_pipeline_cloudrequestengine/readme\.md$'
    '^pipeline/fiftyone_pipeline_cloudrequestengine/src/fiftyone_pipeline_cloudrequestengine/(constants|cloudrequestengine)\.py$'
    '^pipeline/fiftyone_pipeline_cloudrequestengine/tests/test_cloudrequestengine\.py$'
    '^pipeline/fiftyone_pipeline_cloudrequestengine/examples/tests/test_example_utils\.py$'
    '^pipeline/fiftyone_pipeline_did/readme\.md$'
    '^pipeline/fiftyone_pipeline_did/src/fiftyone_pipeline_did/did_client\.py$'
    '^pipeline/fiftyone_pipeline_did/examples/creator_context_web/server\.py$'
    '^pipeline/fiftyone_pipeline_did/tests/test_(did_client|creator_context_server|live_cloud)\.py$'
)

# Whether a path from the root of the repository, written with forward
# slashes, is one of the files that may name an old variable.
function Test-FallbackPath([string]$Relative) {
    foreach ($pattern in $script:FallbackPaths) {
        if ($Relative -match $pattern) {
            return $true
        }
    }
    return $false
}

# The problems on one line, each as its kind, 'digit' or 'fallback', and the
# text matched.
function Find-EnvironmentNameProblem([string]$Line) {
    $Line = $script:DeprecatedReadPattern.Replace($Line, '$1""')
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
$allowed = 0
$skipped = @()
foreach ($relative in $tracked) {
    if ($relative -eq $ownTests -or (Test-FallbackPath $relative)) {
        $allowed++
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
    "$($skipped -join ', '), and $allowed left out, being $ownTests and " +
    'the files that may name an old variable')

if ($found.Count -gt 0 -or $fallbacks.Count -gt 0) {
    Write-Output $found
    Write-Output $fallbacks
    throw ("$($found.Count) names start with a digit, which a POSIX shell " +
        'cannot set, so each must start with an underscore, and ' +
        "$($fallbacks.Count) old names are read, set or kept outside the " +
        'deprecated reads and the files that may name one.')
}

Write-Output ('No tracked file names a variable starting with a digit, or ' +
    'an old name outside the deprecated reads.')

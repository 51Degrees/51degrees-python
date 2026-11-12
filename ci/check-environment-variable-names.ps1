# Every 51Degrees environment variable name in this repository starts with an
# underscore, because a POSIX shell cannot set a name that starts with a digit,
# and everything documents that one name. This reads every file git tracks,
# which leaves out build output and the submodules, and fails on any name
# that starts with the digit and on any old name.
#
# A variable whose name changed is still read under its old name when the new
# one is not set, which is deprecated. So an old name is left alone in the two
# places that read needs it. One is a line where the old name is the argument
# straight after its _51DEGREES_ name, which is how each deprecated read is
# written. The other is the files $FallbackNames lists, each of which may hold
# the old names it is listed with and no others.
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

# The old names each file may hold. The files are the ones that hold the
# deprecated constants, the documentation that says an old name is still
# read, the tests that set an old name to check it is read, and the lists of
# names tox passes to the tests. A file is given by its path from the root of
# the repository, and may hold only the names it is listed with, so any other
# old name still fails there, and so does any other name that starts with a
# digit. The names that are matched wherever they appear are built from
# pieces, so that this file does not name one itself.
$endpointOld = 'FOD_CLOUD' + '_API_URL'
$ipiFileOld = 'IPINTELLIGENCE' + 'DATAFILE'
$performanceOld = 'run_performance' + '_tests'
$ddPathOld = '5' + '1DEGREES_DD_PATH'
$script:FallbackNames = @(
    @{
        Names = @($ddPathOld, 'LICENSE_KEY')
        Paths = @(
            'device-detection/fiftyone_devicedetection_examples/tests/test_environment_names.py'
        )
    }
    @{
        Names = @($ddPathOld, 'cloud_endpoint', 'license_key', 'resource_key')
        Paths = @(
            'device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py'
        )
    }
    @{
        Names = @($endpointOld)
        Paths = @(
            'pipeline/fiftyone_pipeline_cloudrequestengine/examples/tox.ini'
            'pipeline/fiftyone_pipeline_cloudrequestengine/readme.md'
            'pipeline/fiftyone_pipeline_cloudrequestengine/src/fiftyone_pipeline_cloudrequestengine/cloudrequestengine.py'
            'pipeline/fiftyone_pipeline_cloudrequestengine/src/fiftyone_pipeline_cloudrequestengine/constants.py'
            'pipeline/fiftyone_pipeline_cloudrequestengine/tests/test_cloudrequestengine.py'
            'pipeline/fiftyone_pipeline_did/examples/creator_context_web/server.py'
            'pipeline/fiftyone_pipeline_did/readme.md'
            'pipeline/fiftyone_pipeline_did/src/fiftyone_pipeline_did/did_client.py'
            'pipeline/fiftyone_pipeline_did/tests/test_did_client.py'
            'pipeline/fiftyone_pipeline_did/tox.ini'
        )
    }
    @{
        Names = @($endpointOld, 'LICENSE_KEY', 'RESOURCE_KEY')
        Paths = @(
            'pipeline/fiftyone_pipeline_did/tests/test_creator_context_server.py'
        )
    }
    @{
        Names = @($ipiFileOld)
        Paths = @(
            'ip-intelligence/fiftyone_ipintelligence_examples/tox.ini'
            'ip-intelligence/fiftyone_ipintelligence_onpremise/tests/test_environment_names.py'
            'ip-intelligence/fiftyone_ipintelligence_onpremise/tox.ini'
        )
    }
    @{
        Names = @($ipiFileOld, 'LICENSE_KEY')
        Paths = @(
            'ip-intelligence/fiftyone_ipintelligence_examples/tests/test_environment_names.py'
        )
    }
    @{
        Names = @($ipiFileOld, 'cloud_endpoint', 'license_key', 'resource_key')
        Paths = @(
            'ip-intelligence/fiftyone_ipintelligence_examples/src/fiftyone_ipintelligence_examples/example_utils.py'
        )
    }
    @{
        Names = @('cloud_endpoint', 'cloud_request_origin', 'license_key', 'resource_key')
        Paths = @(
            'pipeline/fiftyone_pipeline_cloudrequestengine/examples/src/fiftyone_pipeline_examples/example_utils.py'
        )
    }
    @{
        Names = @('license_key', 'resource_key')
        Paths = @(
            'pipeline/fiftyone_pipeline_did/tests/test_live_cloud.py'
        )
    }
    @{
        Names = @($performanceOld)
        Paths = @(
            'device-detection/fiftyone_devicedetection_examples/tox.ini'
        )
    }
)

# The old names a file may hold, given its path from the root of the
# repository written with forward slashes. Nothing for any other file.
function Get-FallbackName([string]$Relative) {
    foreach ($entry in $script:FallbackNames) {
        if ($entry.Paths -ccontains $Relative) {
            $entry.Names
        }
    }
}

# The problems on one line, each as its kind, 'digit' or 'fallback', and the
# text matched. Allowed holds the old names the line's file may hold, which
# are taken out of the line, in the case they are written in, before the
# line is checked.
function Find-EnvironmentNameProblem([string]$Line, [string[]]$Allowed = @()) {
    $Line = $script:DeprecatedReadPattern.Replace($Line, '$1""')
    if ($Allowed.Count -gt 0) {
        $names = ($Allowed | ForEach-Object { [regex]::Escape($_) }) -join '|'
        $Line = [regex]::Replace(
            $Line, "(?<![A-Za-z0-9_])(?:$names)(?![A-Za-z0-9_])", '')
    }
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
    $allowedNames = @(Get-FallbackName $relative)
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
        foreach ($problem in Find-EnvironmentNameProblem $line $allowedNames) {
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
        "$($fallbacks.Count) old names are read, set or kept outside the " +
        'deprecated reads and the files listed with them.')
}

Write-Output ('No tracked file names a variable starting with a digit, or ' +
    'an old name outside the deprecated reads.')

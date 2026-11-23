# Every environment variable this repository defines is named _51DEGREES_<NAME>,
# so wherever it appears it is clearly 51Degrees. This reads every file git
# tracks, which leaves out build output and the submodules, and fails on any
# line that reads or sets an environment variable under another name.
#
# A name that GitHub, the operating system or a tool defines is used as it
# is. $PlatformNames lists the ones this repository uses.
#
# Only a name written out where a variable is read or set is checked. A
# pipeline setting, a builder parameter and a request's own environ are not
# environment variables of the process, so they are left alone.
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

# What every name this repository defines starts with.
$script:Prefix = '_51DEGREES_'

# Names GitHub, the operating system, Python, pytest and Flask define. Any
# name starting GITHUB_ is GitHub's.
$script:PlatformNames = @(
    'FLASK_APP', 'PATH', 'PSModulePath', 'PYTEST_ADDOPTS', 'PYTHONPATH',
    'TEMP', 'TMP', 'TMPDIR')
$script:PlatformPrefixes = @('GITHUB_')

$name = '(?<name>[A-Za-z0-9_]+)'
$quoted = "['`"]$name['`"]"

# Each way a line reads or sets an environment variable by a name written out.
$script:ReadOrSetPatterns = @(
    # Python: a name given to os.environ, to its get, pop and setdefault, to
    # os.getenv and to pytest's setenv and delenv, and a name looked for in
    # os.environ.
    ('os\.environ(?:\.get|\.pop|\.setdefault)?\s*[\(\[]\s*' + $quoted)
    ('os\.getenv\(\s*' + $quoted)
    ($quoted + '\s+(?:not\s+)?in\s+os\.environ')
    ('\.(?:setenv|delenv)\(\s*' + $quoted)
    # PowerShell: a name after the env: prefix, with or without braces, a
    # path on the Env: drive, and the [Environment] methods.
    ('\$\{?env:' + $name)
    ('(?<![A-Za-z0-9_$\{])Env:\\?' + $name)
    ('EnvironmentVariable\(\s*' + $quoted)
    # A workflow expression that reads the env context.
    ('\$\{\{[^}]*\benv\.' + $name)
    # A shell's export of a name with a value.
    ('^\s*export\s+' + $name + '=')
) | ForEach-Object {
    [regex]::new($_, [Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

# A key of a workflow's env map, which is written in upper case, such as
# "NAME: value".
$script:WorkflowKeyPattern = [regex]::new('^\s+(?<name>[A-Z_][A-Z0-9_]*):(?:\s|$)')

# Whether a name may be read or set: one this repository defines, or one the
# platform does.
function Test-EnvironmentName([string]$Name) {
    if ($Name.StartsWith($script:Prefix, [StringComparison]::Ordinal)) {
        return $true
    }
    if ($script:PlatformNames -contains $Name) {
        return $true
    }
    foreach ($prefix in $script:PlatformPrefixes) {
        if ($Name.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

# The names a line reads or sets that it may not, each once. Relative is the
# file's path from the root of the repository, which says whether the line is
# a workflow's.
function Find-EnvironmentNameProblem([string]$Line, [string]$Relative = '') {
    $names = @()
    foreach ($pattern in $script:ReadOrSetPatterns) {
        foreach ($match in $pattern.Matches($Line)) {
            $names += $match.Groups['name'].Value
        }
    }
    if ($Relative -match '^\.github/workflows/[^/]+\.ya?ml$') {
        $match = $script:WorkflowKeyPattern.Match($Line)
        if ($match.Success) {
            $names += $match.Groups['name'].Value
        }
    }
    $names | Where-Object { -not (Test-EnvironmentName $_) } |
        Select-Object -Unique
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

# The tests of this script name the forms it fails on, on purpose.
$ownTests = 'ci/check-environment-variable-names.Tests.ps1'

$found = @()
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
        foreach ($problem in Find-EnvironmentNameProblem $line $relative) {
            $found += "${relative}:${lineNumber}: $problem"
        }
    }
}

Write-Output ("$read paths read, $($skipped.Count) skipped as not files: " +
    "$($skipped -join ', '), and $ownTests left out")

if ($found.Count -gt 0) {
    Write-Output $found
    throw ("$($found.Count) environment variables are read or set under a " +
        "name that does not start with $($script:Prefix) and is not one the " +
        'platform defines.')
}

Write-Output ('Every environment variable a tracked file reads or sets ' +
    "starts with $($script:Prefix) or is one the platform defines.")

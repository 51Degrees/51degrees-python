param (
    [Parameter(Mandatory)][string]$RepoPath,
    [Parameter(Mandatory)]$Package,
    [Parameter(Mandatory)][string]$From,
    [Parameter(Mandatory)][string[]]$Files
)
$ErrorActionPreference = "Stop"

# Called by the release plan for each package with changed files left once
# the Ignore globs have left theirs out, and returns the files that count.
# A pyproject.toml, setup.py or setup.cfg whose change since $From is only to
# the description, keywords, urls, classifiers, readme, authors or maintainers
# does not count, which release-plan-filter.py works out. Every other file
# counts.
#
# Python is required rather than optional, because a job that counted every
# file would plan different releases from a job that could compare them.

$manifests = 'pyproject.toml', 'setup.py', 'setup.cfg'
$compare = @($Files | Where-Object { (Split-Path -Leaf $_) -in $manifests })
$counted = @($Files | Where-Object { (Split-Path -Leaf $_) -notin $manifests })

if ($compare.Count -gt 0) {
    $python = Get-Command python, python3 -CommandType Application `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $python) {
        throw "Python is needed to tell whether a change to " +
            "$($compare -join ', ') is only to metadata, and none was found."
    }
    $PSNativeCommandUseErrorActionPreference = $false
    $script = Join-Path $PSScriptRoot 'release-plan-filter.py'
    $changed = @(& $python.Source -I $script $RepoPath $From @compare)
    if ($LASTEXITCODE -ne 0) {
        throw "release-plan-filter.py failed for $($Package.Name) since $From."
    }
    $counted += $changed | Where-Object { $_ }
}

$counted

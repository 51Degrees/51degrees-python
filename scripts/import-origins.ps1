<#
.SYNOPSIS
Brings pipeline-python, device-detection-python, location-python and
ip-intelligence-python into this repository with their full history, each in a
folder named without the language (pipeline/, device-detection/, ...), and tags
each released package at its current version. Run once, by hand, at the
cut-over, in a clone of 51degrees-python. It never pushes.

.DESCRIPTION
Each repository is added with 'git subtree add' without --squash, into a
folder of its own name, as 51degrees-cxx was. That keeps every original commit
SHA, so SHAs quoted in old issues and pull requests resolve here, and leaves
every file at its final path, so no move or path rewrite follows.

The root files (ci/, .github/, README.md, AGENTS.md, LICENSE, .gitignore and
the root .gitmodules) are expected in the working tree, not yet committed. They are
committed after the imports, together with the removal of the four imported
.gitmodules files, which git does not read below the root.

Each package that has been released is then tagged '<package>/<version>' at
that commit, at the version its old repository last released, so its version
stream continues here. That version is checked against PyPI first, and the
script stops if they differ. Packages never released (IP Intelligence) are
not tagged: their first release takes FirstVersion from ci/packages.json.

Check the result, then push main and the tags yourself.

.PARAMETER OrgUrl
Where the four repositories are. ip-intelligence-python must be readable by
whoever runs this.
#>
param (
    [string]$OrgUrl = 'https://github.com/51Degrees'
)
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$repoRoot = Split-Path $PSScriptRoot
Set-Location $repoRoot

# Each old repository and the folder it goes into. The folder drops the
# language from the name, because the whole repository is Python. Pipeline
# first, because the others depend on it; the order only affects how the
# history reads.
$origins = [ordered]@{
    'pipeline-python' = 'pipeline'
    'device-detection-python' = 'device-detection'
    'location-python' = 'location'
    'ip-intelligence-python' = 'ip-intelligence'
}

# 'git subtree add' needs a commit to add to.
# An empty repository has no HEAD, which is the answer here, not an error, so
# this one command may fail without stopping the script.
$PSNativeCommandUseErrorActionPreference = $false
$null = git rev-parse --verify --quiet HEAD 2>$null
$hasCommit = $LASTEXITCODE -eq 0
$PSNativeCommandUseErrorActionPreference = $true
if ($hasCommit -eq $false) {
    $global:LASTEXITCODE = 0
    git commit --allow-empty -m 'Start the 51degrees-python repository'
}

foreach ($origin in $origins.Keys) {
    $folder = $origins[$origin]
    if ((Test-Path $folder) -eq $true) {
        throw "'$folder' already exists here; this script runs once, on a fresh clone"
    }
    git fetch --no-tags "$OrgUrl/$origin.git" main
    $sha = git rev-parse FETCH_HEAD
    git subtree add --prefix=$folder $sha `
        -m "Import $origin into $folder/ at $sha with its full history"
}

# The imported .gitmodules files describe the same submodules as the root one,
# with paths relative to the old repositories, and git reads only the root.
foreach ($folder in $origins.Values) {
    $modules = Join-Path $folder '.gitmodules'
    if ((Test-Path $modules) -eq $true) {
        git rm --quiet $modules
    }
}
git add ci .github README.md AGENTS.md LICENSE .gitignore .gitmodules scripts
git commit -m 'Add the root CI, README, AGENTS and submodules'
git submodule sync --recursive
git submodule update --init --recursive

# Tag every released package at the version its old repository last released.
$packages = Get-Content -Raw ci/packages.json | ConvertFrom-Json
$released = $packages | Where-Object {
    $_.Publish -eq $true -and [string]::IsNullOrEmpty($_.FirstVersion) -eq $true
}
$originVersions = @{}
foreach ($package in $released) {
    # The product is the folder; its tags are in the old repository.
    $origin = ($origins.GetEnumerator() |
        Where-Object { $_.Value -eq $package.Product }).Key
    if ($originVersions.ContainsKey($origin) -eq $false) {
        $versions = git ls-remote --tags --refs "$OrgUrl/$origin.git" |
            ForEach-Object { ($_ -split 'refs/tags/')[1] } |
            Where-Object { $_ -match '^\d+\.\d+\.\d+$' } |
            Sort-Object { [version]$_ }
        $originVersions[$origin] = @($versions)[-1]
    }
    $version = $originVersions[$origin]

    # The tag starts the package's version stream here, so it must be the
    # number PyPI has. A mismatch means the old repository and PyPI disagree,
    # which someone has to resolve before the stream continues.
    $pypiName = $package.Name -replace '_', '-'
    $pypi = (Invoke-RestMethod "https://pypi.org/pypi/$pypiName/json").info.version
    if ($pypi -ne $version) {
        throw "$($package.Name): $origin last released $version, but PyPI has $pypi"
    }
    git tag "$($package.Name)/$version"
    Write-Output "Tagged $($package.Name)/$version"
}

Write-Output ""
Write-Output "Done, nothing pushed. Check the history and the tags, then push"
Write-Output "main and the tags."

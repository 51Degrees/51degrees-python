param (
    [string]$RepoName = '.'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# The highest minimum version each package here is required at by another
# package here, read from the install_requires of every setup.py, with the
# package that names it.
function Get-RequiredMinimums($RepoName, $Packages) {
    $minimums = @{}
    foreach ($package in $Packages) {
        $setup = Join-Path $RepoName $package.Path 'setup.py'
        if (-not (Test-Path $setup)) {
            continue
        }
        $text = Get-Content $setup -Raw
        $pattern = '["''](?<name>[A-Za-z0-9_.-]+)\s*>=\s*(?<version>\d+(\.\d+)+)["'']'
        foreach ($match in [regex]::Matches($text, $pattern)) {
            $name = $match.Groups['name'].Value
            $version = [version]$match.Groups['version'].Value
            if (-not $minimums.ContainsKey($name) -or
                    $minimums[$name].Version -lt $version) {
                $minimums[$name] = [pscustomobject]@{
                    Version = $version
                    By = $package.Name
                }
            }
        }
    }
    return $minimums
}

# Writes the version.txt that each published package's setup.py reads. Without
# one a package installed from this checkout is 0.0.0, which is below the
# versions the packages here require of each other, so pip refuses it, or
# replaces it with a release from PyPI. Each package gets the version this
# commit would release it at, as the publish gives it when it builds the
# package, or its last release when this commit would not release it.
#
# When that is below the version another package here requires of it, no
# release from this commit would meet the requirement, and the package that
# names it could not be installed once published. So the script stops, before
# writing anything, and names both versions.
$plan = @(Get-ReleasePlan $RepoName)
$published = @(Get-Packages $RepoName | Where-Object { $_.Publish -eq $true })
$minimums = Get-RequiredMinimums $RepoName $published
$versions = [ordered]@{}
$problems = @()
foreach ($package in $published) {
    # A version.txt committed with the package is left as it is.
    if (git -C $RepoName ls-files -- "$($package.Path)/version.txt") {
        continue
    }
    $release = $plan | Where-Object { $_.Name -eq $package.Name }
    if ($null -ne $release) {
        $version = $release.Version
        $source = "the release plan gives it $version"
    } else {
        $version = "$((Get-ReleasedVersions $RepoName $package.Name)[-1])"
        $source = ("the release plan leaves it out, so it stays at its " +
            "last release, $version")
    }
    $required = $minimums[$package.Name]
    if ($null -ne $required -and [version]$version -lt $required.Version) {
        $problems += ("$($package.Name) is required at " +
            "$($required.Version) or later by $($required.By), but $source.")
    }
    $versions[$package] = $version
}
if ($problems.Count -gt 0) {
    throw (($problems + ("No release from this commit would meet these " +
        "requirements. Find why the release plan does not release each " +
        "package at the version required, or lower the requirement.")) -join
        [Environment]::NewLine)
}
foreach ($package in $versions.Keys) {
    $version = $versions[$package]
    $version | Out-File (Join-Path $RepoName $package.Path 'version.txt')
    Write-Output "$($package.Name) $version"
}

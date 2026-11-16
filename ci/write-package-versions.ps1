param (
    [string]$RepoName = '.'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# The lowest version each package here is required at by another package
# here, read from the install_requires of every setup.py. A package this
# commit would not release keeps its last release, which can be below a
# minimum that names the version this release gives it, and pip then looks
# for that version on a package index, where it does not exist yet.
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
                    $minimums[$name] -lt $version) {
                $minimums[$name] = $version
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
# package, or its last release when this commit would not release it, and
# never less than the version another package here requires of it.
$plan = @(Get-ReleasePlan $RepoName)
$published = @(Get-Packages $RepoName | Where-Object { $_.Publish -eq $true })
$minimums = Get-RequiredMinimums $RepoName $published
foreach ($package in $published) {
    # A version.txt committed with the package is left as it is.
    if (git -C $RepoName ls-files -- "$($package.Path)/version.txt") {
        continue
    }
    $release = $plan | Where-Object { $_.Name -eq $package.Name }
    if ($null -ne $release) {
        $version = $release.Version
    } else {
        $version = "$((Get-ReleasedVersions $RepoName $package.Name)[-1])"
    }
    $required = $minimums[$package.Name]
    if ($null -ne $required -and [version]$version -lt $required) {
        Write-Output ("$($package.Name) $version is below the $required " +
            "another package here requires, so it is written as $required")
        $version = "$required"
    }
    $version | Out-File (Join-Path $RepoName $package.Path 'version.txt')
    Write-Output "$($package.Name) $version"
}

param (
    [string]$RepoName = '.'
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'packages.ps1')

# Writes the version.txt that each published package's setup.py reads. Without
# one a package installed from this checkout is 0.0.0, which is below the
# versions the packages here require of each other, so pip refuses it, or
# replaces it with a release from PyPI. Each package gets the version this
# commit would release it at, as the publish gives it when it builds the
# package, or its last release when this commit would not release it.
$plan = @(Get-ReleasePlan $RepoName)
$published = @(Get-Packages $RepoName | Where-Object { $_.Publish -eq $true })
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
    $version | Out-File (Join-Path $RepoName $package.Path 'version.txt')
    Write-Output "$($package.Name) $version"
}

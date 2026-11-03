param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
	[Parameter(Mandatory=$true)]
    [string]$Version
)

./python/build-package-pypi.ps1 -RepoName $RepoName -Version $Version -Packages .

exit $LASTEXITCODE

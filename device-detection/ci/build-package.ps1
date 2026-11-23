param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
	[Parameter(Mandatory=$true)]
    [string]$Version
)

$packages = "fiftyone_devicedetection_shared", "fiftyone_devicedetection_cloud", "fiftyone_devicedetection_onpremise", "fiftyone_devicedetection"
./python/build-package-pypi.ps1 -RepoName $RepoName -Version $Version -Packages $packages

exit $LASTEXITCODE

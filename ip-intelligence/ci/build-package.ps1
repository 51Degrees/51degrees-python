param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
	[Parameter(Mandatory=$true)]
    [string]$Version
)

$packages = "fiftyone_ipintelligence_shared", "fiftyone_ipintelligence_cloud", "fiftyone_ipintelligence_onpremise", "fiftyone_ipintelligence_translation", "fiftyone_ipintelligence"
./python/build-package-pypi.ps1 -RepoName $RepoName -Version $Version -Packages $packages

exit $LASTEXITCODE

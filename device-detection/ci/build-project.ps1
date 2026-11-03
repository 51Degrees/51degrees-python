param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

$packages = "fiftyone_devicedetection_shared", "fiftyone_devicedetection_cloud", "fiftyone_devicedetection_onpremise", "fiftyone_devicedetection", "fiftyone_devicedetection_examples"
./python/build-project.ps1 -RepoName $RepoName -Packages $packages -WithExtensions "fiftyone_devicedetection_onpremise"

exit $LASTEXITCODE

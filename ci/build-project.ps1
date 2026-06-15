param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

$packages = "fiftyone_ipintelligence_shared", "fiftyone_ipintelligence_cloud", "fiftyone_ipintelligence_onpremise", "fiftyone_ipintelligence", "fiftyone_ipintelligence_examples"
./python/build-project.ps1 -RepoName $RepoName -Packages $packages -WithExtensions "fiftyone_ipintelligence_onpremise"

exit $LASTEXITCODE

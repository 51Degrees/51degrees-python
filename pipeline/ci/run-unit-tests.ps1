param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

# The tests marked live call the cloud service, and no key reaches the unit
# step, so they are left to run-integration-tests.ps1. Only a package whose
# tox.ini passes PYTEST_ADDOPTS sees the selection.
$addopts = $env:PYTEST_ADDOPTS
$env:PYTEST_ADDOPTS = '-m "not live"'
try {
    $packages = "fiftyone_pipeline_core", "fiftyone_pipeline_engines", "fiftyone_pipeline_engines_fiftyone", "fiftyone_pipeline_translation", "fiftyone_pipeline_did"
    ./python/run-unit-tests.ps1 -RepoName $RepoName -Packages $packages
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

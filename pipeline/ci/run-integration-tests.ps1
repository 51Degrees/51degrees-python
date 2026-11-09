param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [Hashtable]$Keys
)

if (!$Keys.TestResourceKey) {
    throw "No TestResourceKey was passed, so the cloud tests cannot call " +
        "the cloud service. The workflows set it from the " +
        "_51DEGREES_RESOURCE_KEY_BESPOKE secret."
}

# The examples call the cloud service, so they are integration tests rather
# than unit tests. Listing them here runs them on every Python version and
# operating system in options.json, and in the nightly, which a standalone
# workflow did not.
#
# This script's common-ci counterpart sets resource_key from the
# TestResourceKey secret, and license_key from the DeviceDetection secret.
# The workflows pass DeviceDetection for Device Detection's data files. It is
# not a licence key for the cloud service, so the examples' licence-key tests
# failed with it. They are not given it, and skip themselves as they did when
# pipeline was its own repository, until a cloud licence key is passed.
#
# The 51Did package runs only its tests marked live here, as its others ran
# in the unit step. Its tier tests need a key for another tier, which only
# the Cloud 51Did workflow has. Only a package whose tox.ini passes
# PYTEST_ADDOPTS sees the selection. Its build needs the OWID source, which
# build-project.ps1 copies, and the publish workflow's test job does not run
# that script, so it is copied here too.
& "$PSScriptRoot/copy-owid-source.ps1" -RepoRoot $RepoName
$packages = "fiftyone_pipeline_cloudrequestengine", "fiftyone_pipeline_cloudrequestengine/examples", "fiftyone_pipeline_did"
$pipelineKeys = $Keys.Clone()
$pipelineKeys.Remove('DeviceDetection')
$addopts = $env:PYTEST_ADDOPTS
$env:PYTEST_ADDOPTS = '-m "live and not tier"'
try {
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $pipelineKeys
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

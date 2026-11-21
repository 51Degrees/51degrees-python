param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    # The secrets, which common-ci passes on. No key is read from them: each
    # is read from the environment under its _51DEGREES_ name.
    [Hashtable]$Keys = @{}
)

if (!$env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
    throw "_51DEGREES_RESOURCE_KEY_BESPOKE is not set, so the cloud tests " +
        "cannot call the cloud service. common-ci exports it from the " +
        "organization secret of that name, which the workflows pass with " +
        "'secrets: inherit'."
}

# The examples call the cloud service, so they are integration tests rather
# than unit tests. Listing them here runs them on every Python version and
# operating system in options.json, and in the nightly, which a standalone
# workflow did not.
#
# _51DEGREES_LICENSE_KEY is the data license, for Device Detection's data
# files, and not a license key for the cloud service. The license-key tests
# read _51DEGREES_LICENSE_KEY_BESPOKE instead, and skip naming it when it is
# not set. The 51Did tests read _51DEGREES_RESOURCE_KEY_51DID and
# _51DEGREES_LICENSE_KEY_51DID, which common-ci exports.
#
# The 51Did package runs only its tests marked live here, as its others ran
# in the unit step. Its tier tests need a key for another tier, which only
# the Cloud 51Did workflow has. Only a package whose tox.ini passes
# PYTEST_ADDOPTS sees the selection. Its build needs the OWID source, which
# build-project.ps1 copies, and the publish workflow's test job does not run
# that script, so it is copied here too.
& "$PSScriptRoot/copy-owid-source.ps1" -RepoRoot $RepoName
$packages = "fiftyone_pipeline_cloudrequestengine", "fiftyone_pipeline_cloudrequestengine/examples", "fiftyone_pipeline_did"
# The tests and examples read the resource key from _51DEGREES_RESOURCE_KEY,
# which common-ci fills from _51DEGREES_RESOURCE_KEY_BESPOKE. It is filled
# here too when it is empty, and never replaced.
if (!$env:_51DEGREES_RESOURCE_KEY) {
    $env:_51DEGREES_RESOURCE_KEY = $env:_51DEGREES_RESOURCE_KEY_BESPOKE
}

$addopts = $env:PYTEST_ADDOPTS
$env:PYTEST_ADDOPTS = '-m "live and not tier"'
try {
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $Keys
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

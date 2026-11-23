param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    # The secrets, which common-ci passes on. No key is read from them: each
    # is read from the environment under its _51DEGREES_ name.
    [Hashtable]$Keys = @{}
)

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
# PYTEST_ADDOPTS sees the selection, so the 51Did package is run on its own,
# after the others. Its build needs the OWID source, which build-project.ps1
# copies, and the publish workflow's test job does not run that script, so
# it is copied here too.
#
# Without a resource key the tests that need one, which are marked live, are
# left out and every other test runs. That leaves nothing of the 51Did
# package, so it is not run. A live test still fails when it finds no key, so
# a key that is passed but does not reach it is not missed. The selection is
# added to any options a caller set in PYTEST_ADDOPTS.
$packages = "fiftyone_pipeline_cloudrequestengine", "fiftyone_pipeline_cloudrequestengine/examples"
$pipelineKeys = $Keys.Clone()
$pipelineKeys.Remove('DeviceDetection')
# The tests and examples read the resource key from _51DEGREES_RESOURCE_KEY,
# which common-ci fills from _51DEGREES_RESOURCE_KEY_BESPOKE. It is filled
# here too when it is empty, and never replaced.
if (!$env:_51DEGREES_RESOURCE_KEY) {
    $env:_51DEGREES_RESOURCE_KEY = $env:_51DEGREES_RESOURCE_KEY_BESPOKE
}

$failed = $false
$addopts = $env:PYTEST_ADDOPTS
try {
    if (!$env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
        Write-Output "::warning title=No resource key::_51DEGREES_RESOURCE_KEY_BESPOKE is not set, so the tests that need a resource key are skipped. They are marked live, and the other integration tests run. fiftyone_pipeline_did runs only live tests here, so it is skipped. common-ci exports it from the organization variable of that name."
        $env:PYTEST_ADDOPTS = "$addopts -m `"not live`"".Trim()
    }
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $pipelineKeys
    if ($LASTEXITCODE -ne 0) { $failed = $true }

    if ($env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
        # common-ci's script combines the coverage of the packages it ran
        # into .coverage, and a second run replaces that file, so the first
        # run's is kept under a name the second run's combine reads.
        $coverage = Join-Path $RepoName '.coverage'
        if (Test-Path $coverage) {
            Move-Item -Force $coverage (Join-Path $RepoName '.coverage.cloudrequestengine')
        }
        & "$PSScriptRoot/copy-owid-source.ps1" -RepoRoot $RepoName
        $env:PYTEST_ADDOPTS = '-m "live and not tier"'
        ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages "fiftyone_pipeline_did" -Keys $pipelineKeys
        if ($LASTEXITCODE -ne 0) { $failed = $true }
    }
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit ($failed ? 1 : 0)

param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [Hashtable]$Keys
)

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
# The tests read the resource key from _51DEGREES_RESOURCE_KEY, and common-ci
# sets only the older resource_key, so the key is set here.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey

$failed = $false
$addopts = $env:PYTEST_ADDOPTS
try {
    if (!$Keys.TestResourceKey) {
        Write-Output "::warning title=No resource key::No TestResourceKey was passed, so the tests that need a resource key are skipped. They are marked live, and the other integration tests run. fiftyone_pipeline_did runs only live tests here, so it is skipped. The workflows set it from the _51DEGREES_RESOURCE_KEY_BESPOKE secret."
        $env:PYTEST_ADDOPTS = "$addopts -m `"not live`"".Trim()
    }
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $pipelineKeys
    if ($LASTEXITCODE -ne 0) { $failed = $true }

    if ($Keys.TestResourceKey) {
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

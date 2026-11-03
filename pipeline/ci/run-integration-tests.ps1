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
$packages = "fiftyone_pipeline_cloudrequestengine", "fiftyone_pipeline_cloudrequestengine/examples"
$pipelineKeys = $Keys.Clone()
$pipelineKeys.Remove('DeviceDetection')
./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $pipelineKeys

exit $LASTEXITCODE

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

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages . -Keys $Keys

exit $LASTEXITCODE

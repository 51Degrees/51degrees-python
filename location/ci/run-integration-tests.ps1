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

# The examples and tests read the resource key from _51DEGREES_RESOURCE_KEY,
# and common-ci sets only the older resource_key, so the key is set here.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages . -Keys $Keys

exit $LASTEXITCODE

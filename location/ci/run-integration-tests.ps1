param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [Hashtable]$Keys
)

# Without a resource key the tests that need one, which are marked live, are
# left out and every other test runs. A live test still fails when it finds
# no key, so a key that is passed but does not reach it is not missed.
$addopts = $env:PYTEST_ADDOPTS
if (!$Keys.TestResourceKey) {
    Write-Output "::warning title=No resource key::No TestResourceKey was passed, so the tests that need a resource key are skipped. They are marked live, and the other integration tests run. The workflows set it from the _51DEGREES_RESOURCE_KEY_BESPOKE secret."
    $env:PYTEST_ADDOPTS = '-m "not live"'
}

# The examples and tests read the resource key from _51DEGREES_RESOURCE_KEY,
# and common-ci sets only the older resource_key, so the key is set here.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey

try {
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages . -Keys $Keys
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

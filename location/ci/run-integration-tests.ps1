param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    # The secrets, which common-ci passes on. No key is read from them: each
    # is read from the environment under its _51DEGREES_ name.
    [Hashtable]$Keys = @{}
)

# Without a resource key the tests that need one, which are marked live, are
# left out and every other test runs. A live test still fails when it finds
# no key, so a key that is passed but does not reach it is not missed.
# The selection is added to any options a caller set in PYTEST_ADDOPTS.
$addopts = $env:PYTEST_ADDOPTS
if (!$env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
    Write-Output "::warning title=No resource key::_51DEGREES_RESOURCE_KEY_BESPOKE is not set, so the tests that need a resource key are skipped. They are marked live, and the other integration tests run. common-ci exports it from the organization variable of that name."
    $env:PYTEST_ADDOPTS = "$addopts -m `"not live`"".Trim()
}

try {
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages . -Keys $Keys
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

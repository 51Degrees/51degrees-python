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

# The tests and examples read the resource key from _51DEGREES_RESOURCE_KEY,
# which common-ci fills from _51DEGREES_RESOURCE_KEY_BESPOKE. It is filled
# here too when it is empty, and never replaced.
if (!$env:_51DEGREES_RESOURCE_KEY) {
    $env:_51DEGREES_RESOURCE_KEY = $env:_51DEGREES_RESOURCE_KEY_BESPOKE
}

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages . -Keys $Keys

exit $LASTEXITCODE

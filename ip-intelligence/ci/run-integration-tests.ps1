param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    # The secrets, which common-ci passes on. No key is read from them: each
    # is read from the environment under its _51DEGREES_ name.
    [Hashtable]$Keys = @{}
)

if ($IsWindows) {
    # Shorten the temporary directory path to work around MSVC path lenght limit
    $env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"
    Write-Output $env:TEMP
}

$packages = , "fiftyone_ipintelligence_examples"

# Without a resource key the tests that need one, which are marked live, are
# left out and every other test runs. A live test still fails when it finds
# no key, so a key that is passed but does not reach it is not missed.
# The selection is added to any options a caller set in PYTEST_ADDOPTS.
$addopts = $env:PYTEST_ADDOPTS
if (!$env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
    Write-Output "::warning title=No resource key::_51DEGREES_RESOURCE_KEY_BESPOKE is not set, so the tests that need a resource key are skipped. They are marked live, and the other integration tests run. common-ci exports it from the organization variable of that name."
    $env:PYTEST_ADDOPTS = "$addopts -m `"not live`"".Trim()
}

# Says what the key is entitled to, so a run with no IP data is read as an
# entitlement gap rather than as broken code. Prints product names and tiers
# only, never the key. Found through this script's own folder, because
# common-ci runs it from the common-ci checkout, where
# './ci/report-key-products.ps1' does not exist.
if ($env:_51DEGREES_RESOURCE_KEY_BESPOKE) {
    & (Join-Path $PSScriptRoot 'report-key-products.ps1') -ResourceKey $env:_51DEGREES_RESOURCE_KEY_BESPOKE
}

# nightly-publish-main workflow doesn't create the examples package, so
# install-package.ps1 won't install it and its test dependencies won't get
# installed. That's why we install it here, as a special case.
if ($env:GITHUB_JOB -eq "Test") {
    Write-Output "Installing 'fiftyone_ipintelligence_examples' package to install its dependencies"
    pip install $RepoName/fiftyone_ipintelligence_examples || $(throw "pip install failed")
}

try {
    ./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $Keys
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

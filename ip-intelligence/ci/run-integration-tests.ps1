param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [Hashtable]$Keys
)

if ($IsWindows) {
    # Shorten the temporary directory path to work around MSVC path lenght limit
    $env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"
    Write-Output $env:TEMP
}

$packages = , "fiftyone_ipintelligence_examples"

if (!$Keys.TestResourceKey) {
    throw "No TestResourceKey was passed, so the cloud tests cannot call " +
        "the cloud service. The workflows set it from the " +
        "_51DEGREES_RESOURCE_KEY_BESPOKE secret."
}

# The tests read the resource key from _51DEGREES_RESOURCE_KEY, and common-ci
# sets only the older resource_key, so the key is set here.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey

# Says what that key is entitled to, so a run with no IP data is read as an
# entitlement gap rather than as broken code. Prints product names and tiers
# only, never the key. Found through this script's own folder, because
# common-ci runs it from the common-ci checkout, where
# './ci/report-key-products.ps1' does not exist.
& (Join-Path $PSScriptRoot 'report-key-products.ps1') -ResourceKey $Keys.TestResourceKey

# nightly-publish-main workflow doesn't create the examples package, so
# install-package.ps1 won't install it and its test dependencies won't get
# installed. That's why we install it here, as a special case.
if ($env:GITHUB_JOB -eq "Test") {
    Write-Output "Installing 'fiftyone_ipintelligence_examples' package to install its dependencies"
    pip install $RepoName/fiftyone_ipintelligence_examples || $(throw "pip install failed")
}

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $Keys

exit $LASTEXITCODE

param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

if ($IsWindows) {
    # Shorten the temporary directory path to work around MSVC path lenght limit
    $env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"
    Write-Output $env:TEMP
}

# The cloud package's tests against fixed cloud responses need no resource
# key, no licence key and no network connection. Running them here means a
# broken cloud example shows as red on every build, rather than only when the
# integration tests happen to have a key to run with. Its tests marked live
# call the cloud service, and no key reaches this step, so they are left to
# run-integration-tests.ps1. Only a package whose tox.ini passes
# PYTEST_ADDOPTS sees the selection.
$addopts = $env:PYTEST_ADDOPTS
$env:PYTEST_ADDOPTS = '-m "not live"'
try {
    $packages = "fiftyone_devicedetection_cloud", "fiftyone_devicedetection_onpremise"
    ./python/run-unit-tests.ps1 -RepoName $RepoName -Packages $packages
} finally {
    $env:PYTEST_ADDOPTS = $addopts
}

exit $LASTEXITCODE

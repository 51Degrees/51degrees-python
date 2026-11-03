param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

if ($IsWindows) {
    # Shorten the temporary directory path to work around MSVC path lenght limit
    $env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"
    Write-Output $env:TEMP
}

# The cloud package's tests run against fixed cloud responses, so they need
# no resource key, no licence key and no network connection. Running them
# here means a broken cloud example shows as red on every build, rather than
# only when the integration tests happen to have a key to run with.
$packages = "fiftyone_devicedetection_cloud", "fiftyone_devicedetection_onpremise"
./python/run-unit-tests.ps1 -RepoName $RepoName -Packages $packages

exit $LASTEXITCODE

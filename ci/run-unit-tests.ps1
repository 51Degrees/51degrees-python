param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

if ($IsWindows) {
    # Shorten the temporary directory path to work around MSVC path lenght limit
    $env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"
    Write-Output $env:TEMP
}

# The cloud package tests run against a mocked cloud service so they do
# not require a resource key and can run as unit tests.
$packages = "fiftyone_ipintelligence_shared", "fiftyone_ipintelligence_cloud", "fiftyone_ipintelligence_onpremise", "fiftyone_ipintelligence_translation"
./python/run-unit-tests.ps1 -RepoName $RepoName -Packages $packages

exit $LASTEXITCODE

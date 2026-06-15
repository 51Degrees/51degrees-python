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
    Write-Output "::warning file=$($MyInvocation.ScriptName),line=$($MyInvocation.ScriptLineNumber),title=No Resource Key::No resource key was provided, so cloud integration tests will not run."
}

# nightly-publish-main workflow doesn't create the examples package, so
# install-package.ps1 won't install it and its test dependencies won't get
# installed. That's why we install it here, as a special case.
if ($env:GITHUB_JOB -eq "Test") {
    Write-Output "Installing 'fiftyone_ipintelligence_examples' package to install its dependencies"
    pip install $RepoName/fiftyone_ipintelligence_examples || $(throw "pip install failed")
}

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $Keys

exit $LASTEXITCODE

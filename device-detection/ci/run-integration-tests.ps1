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

$packages = "fiftyone_devicedetection_cloud", "fiftyone_devicedetection_examples"

if (!$Keys.TestResourceKey) {
    Write-Output "::warning file=$($MyInvocation.ScriptName),line=$($MyInvocation.ScriptLineNumber),title=No Resource Key::No resource key was provided, so integration tests will not run."
    return
} elseif (!(Test-Path $RepoName/fiftyone_devicedetection_cloud/tests/51Degrees.csv)) {
    Write-Output "::warning file=$($MyInvocation.ScriptName),line=$($MyInvocation.ScriptLineNumber),title=No CSV File::CSV file wasn't found, so cloud tests will not run."
    $packages = "fiftyone_devicedetection_examples"
}

# nightly-publish-main workflow doesn't create the examples package, so
# install-package.ps1 won't install it and its test dependencies won't get
# installed. That's why we install it here, as a special case.
if ($env:GITHUB_JOB -eq "Test") {
    Write-Output "Installing 'fiftyone_devicedetection_examples' package to install its dependencies"
    pip install $RepoName/fiftyone_devicedetection_examples || $(throw "pip install failed")
}

# Resource key environment variables follow the 51Degrees convention, which
# is that every one of them starts with '_51DEGREES_RESOURCE_KEY'. The name
# used before the convention was adopted is set by common-ci and is still
# read as a fallback, so anything not yet moved over keeps working.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey

./python/run-integration-tests.ps1 -RepoName $RepoName -Packages $packages -Keys $Keys
$failures = @()
if ($LASTEXITCODE -ne 0) {
    $failures += "the Python integration tests exited with code $LASTEXITCODE"
}

# The shared Selenium contract tests are run against the cloud example and the
# on-premise example in turn. Each result is also written as a trx file next
# to the other integration results, so it is published with them.
$resultsDir = (New-Item -ItemType Directory -Force -Path "$RepoName/test-results/integration").FullName

# Get the shared contract tests.
if (-not (Test-Path selenium-api-tests)) {
    git clone --depth 1 https://github.com/51Degrees/selenium-api-tests.git
    if ($LASTEXITCODE -ne 0) { throw "failed to clone selenium-api-tests" }
}

# Settings the suite reads whichever example it drives. CLOUD_ROOT_URL is read
# when the suite starts, so it is needed for the on-premise run too.
$env:CLOUD_ROOT_URL = "https://cloud.51degrees.com/"
$env:PAID_RESOURCE_KEY = $Keys.TestResourceKey
$env:EXAMPLE_LANG = 'python'

# The examples run from their own virtual environment, created once here so a
# running example never holds a file the second setup would need to replace.
# .venv name is already taken by tox, so this venv uses another directory name.
$examplesDir = (Resolve-Path "$PSScriptRoot/../fiftyone_devicedetection_examples").Path
$py = Join-Path $examplesDir ($IsWindows ? ".virtualenv/Scripts/python.exe" : ".virtualenv/bin/python")
Push-Location $examplesDir
try {
    python3 -m venv .virtualenv
    if ($LASTEXITCODE -ne 0) { throw "failed to create the examples virtual environment" }
    & $py -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw "failed to install the examples package" }
} finally { Pop-Location }

# Starts one of this repository's web examples on the given port, waits for it
# to answer, runs the contract tests against it and stops it again. Returns a
# description of the failure, or nothing when every test passed.
function Test-Example([string]$Name, [string]$Module, [int]$Port) {
    Write-Host "Running Selenium tests against the $Name example on port $Port..."
    $example = $null
    try {
        Push-Location $examplesDir
        try {
            $env:PORT = $Port
            $example = & $py -m $Module 2>&1 &
        } finally { Pop-Location }

        # Wait for the example to come up, or to stop.
        $url = "http://localhost:$Port"
        $deadline = (Get-Date).AddSeconds(180)
        $ready = $false
        while (-not $ready -and (Get-Date) -lt $deadline -and $example.State -eq 'Running') {
            try {
                Invoke-WebRequest -Uri $url -TimeoutSec 10 -SkipHttpErrorCheck | Out-Null
                $ready = $true
            } catch {
                Start-Sleep -Seconds 2
            }
        }
        if (-not $ready) {
            return "the $Name example did not answer on $url (job state $($example.State))"
        }

        $env:EXAMPLE_URL = $url
        # Output goes to the host, so that only a failure is returned.
        dotnet test selenium-api-tests -c Release --filter TestCategory=Contract `
            --results-directory $resultsDir --logger "trx;LogFileName=selenium-$Name.trx" `
            --logger "console;verbosity=normal" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            return "the Selenium contract tests against the $Name example exited with code $LASTEXITCODE"
        }
    } finally {
        if ($example) {
            Write-Host ">>> $Name example output >>>"
            Receive-Job $example | Out-Host
            Write-Host "<<< $Name example output <<<"
            Remove-Job -Force $example
        }
    }
}

# The cloud example, pointed at the live cloud.
$env:_51DEGREES_RESOURCE_KEY = $Keys.TestResourceKey
$env:cloud_endpoint = "https://cloud.51degrees.com/api/v4/"
$failures += Test-Example -Name 'cloud' `
    -Module 'fiftyone_devicedetection_examples.cloud.gettingstarted_web' -Port 8097

# The on-premise example. The contract tests need the device type and the
# JavaScript properties, which the Lite data file does not have, so it runs
# against the TAC data file, which is only fetched when a licence is given.
$tac = "$PWD/assets/TAC-HashV41.hash"
if (Test-Path $tac) {
    ${env:51DEGREES_DD_PATH} = (Resolve-Path $tac).Path
    $failures += Test-Example -Name 'onpremise' `
        -Module 'fiftyone_devicedetection_examples.onpremise.gettingstarted_web' -Port 8098
    Remove-Item Env:51DEGREES_DD_PATH
} else {
    Write-Output "::warning file=$($MyInvocation.ScriptName),line=$($MyInvocation.ScriptLineNumber),title=No TAC Data File::The TAC data file wasn't found, so the Selenium tests will not run against the on-premise example."
}

# A failure anywhere above must fail the job. This script is dot-sourced by
# common-ci, so an exit code is lost once a later step runs a command of its
# own, and only an error that stops the script is seen by the job.
$failures = @($failures | Where-Object { $_ })
if ($failures.Count -gt 0) {
    throw "Integration tests failed: $($failures -join '; ')"
}

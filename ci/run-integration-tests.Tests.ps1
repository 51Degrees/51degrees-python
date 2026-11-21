# Tests for the integration test step when no resource key is passed.
#
# Each product's ci/run-integration-tests.ps1 is run as common-ci runs it,
# through ci/dispatch.ps1 and common-ci's steps/run-script.ps1, from a folder
# laid out like a common-ci checkout. Its python/run-integration-tests.ps1 is
# a stand-in that runs no tests and records, for each call, the packages it
# was given and the PYTEST_ADDOPTS the tests would see.

BeforeAll {
    . (Join-Path $PSScriptRoot 'dispatch.ps1')

    # common-ci checked out beside this repository, or wherever COMMON_CI says.
    $commonCi = $env:COMMON_CI
    if ([string]::IsNullOrEmpty($commonCi) -eq $true) {
        $commonCi = Join-Path $PSScriptRoot '..' '..' 'common-ci'
    }
    $script:Steps = Join-Path $commonCi 'steps'
    if ((Test-Path (Join-Path $script:Steps 'run-script.ps1')) -eq $false) {
        throw "common-ci not found at '$commonCi'; set COMMON_CI to a checkout of it"
    }

    $script:Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

    # The products whose integration tests call the cloud service.
    $script:Products = 'device-detection', 'ip-intelligence', 'location',
        'pipeline'

    # The environment variables the scripts set, kept to be put back.
    $script:Saved = '_51DEGREES_RESOURCE_KEY', '_51DEGREES_LICENSE_KEY',
        'PYTEST_ADDOPTS', 'TEMP'

    # The stand-in for common-ci's python/run-integration-tests.ps1. It
    # writes one line of JSON for each call to calls.jsonl in the folder it
    # runs from.
    $script:StandIn = @'
param (
    [Parameter(Mandatory=$true)][string]$RepoName,
    [Parameter(Mandatory=$true)][string[]]$Packages,
    [Parameter(Mandatory=$true)][hashtable]$Keys
)
@{
    Product = Split-Path $RepoName -Leaf
    Packages = @($Packages)
    AddOpts = "$env:PYTEST_ADDOPTS"
} | ConvertTo-Json -Compress | Add-Content (Join-Path $PWD 'calls.jsonl')
$global:LASTEXITCODE = 0
'@

    # A folder laid out like a common-ci checkout, which the step runs in.
    function New-CommonCi {
        $path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        $null = New-Item -ItemType Directory -Force (Join-Path $path 'python')
        Copy-Item -Recurse $script:Steps (Join-Path $path 'steps')
        Set-Content (Join-Path $path 'python' 'run-integration-tests.ps1') `
            $script:StandIn
        return $path
    }

    # The calls the stand-in recorded for a product.
    function Get-Calls([string]$Product) {
        $file = Join-Path $script:CommonCi 'calls.jsonl'
        if ((Test-Path $file) -eq $false) {
            return @()
        }
        return @(Get-Content $file | ForEach-Object { $_ | ConvertFrom-Json } |
            Where-Object Product -eq $Product)
    }
}

Describe 'run-integration-tests.ps1' {

BeforeEach {
    $script:Environment = @{}
    foreach ($name in $script:Saved) {
        $script:Environment[$name] = [Environment]::GetEnvironmentVariable($name)
    }
    $script:CommonCi = New-CommonCi
    Push-Location $script:CommonCi
}

AfterEach {
    Pop-Location
    Remove-Item -Recurse -Force $script:CommonCi
    foreach ($name in $script:Saved) {
        [Environment]::SetEnvironmentVariable($name, $script:Environment[$name])
    }
}

Context 'with no TestResourceKey' {
    BeforeEach {
        $env:PYTEST_ADDOPTS = $null
        $script:Output = Invoke-ProductStep 'run-integration-tests' $script:Repo `
            @{ RepoName = $script:Repo; Keys = @{} } $script:Products *>&1 |
            Out-String
    }

    It 'runs the tests of every product' {
        foreach ($product in $script:Products) {
            (Get-Calls $product).Count | Should -BeGreaterThan 0 -Because $product
        }
    }

    It 'leaves out only the tests marked live, which need a resource key' {
        foreach ($product in $script:Products) {
            foreach ($call in (Get-Calls $product)) {
                $call.AddOpts | Should -Be '-m "not live"' -Because $product
            }
        }
    }

    It 'says for every product that the tests needing a key are skipped' {
        foreach ($product in $script:Products) {
            # What the step printed for this product, between its group
            # markers.
            $group = ($script:Output -split '::group::') |
                Where-Object { $_ -like "run-integration-tests for $product*" }
            $group | Should -Match ("No TestResourceKey was passed, so the " +
                "tests that need a resource key are skipped") -Because $product
        }
    }

    It 'runs the tests of the device detection and IP intelligence examples' {
        (Get-Calls 'device-detection').Packages |
            Should -Contain 'fiftyone_devicedetection_examples'
        (Get-Calls 'device-detection').Packages |
            Should -Contain 'fiftyone_devicedetection_cloud'
        (Get-Calls 'ip-intelligence').Packages |
            Should -Contain 'fiftyone_ipintelligence_examples'
    }

    It 'runs the cloud request engine and its examples, and skips the 51Did live tests' {
        $packages = (Get-Calls 'pipeline').Packages
        $packages | Should -Contain 'fiftyone_pipeline_cloudrequestengine'
        $packages | Should -Contain 'fiftyone_pipeline_cloudrequestengine/examples'
        $packages | Should -Not -Contain 'fiftyone_pipeline_did'
        $script:Output | Should -Match 'fiftyone_pipeline_did.*skipped'
    }

    It 'skips the Selenium contract against the cloud example and saying so' {
        $script:Output | Should -Match 'Selenium contract tests will not run against the cloud example'
        Test-Path (Join-Path $script:CommonCi 'selenium-api-tests') |
            Should -BeFalse
    }
}

Context 'with no TestResourceKey and options a caller set' {
    It 'adds the selection to the options, and puts them back after' {
        $env:PYTEST_ADDOPTS = '-p no:cacheprovider'
        Invoke-ProductStep 'run-integration-tests' $script:Repo `
            @{ RepoName = $script:Repo; Keys = @{} } $script:Products *>&1 |
            Out-Null

        foreach ($product in $script:Products) {
            $calls = Get-Calls $product
            $calls.Count | Should -BeGreaterThan 0 -Because $product
            foreach ($call in $calls) {
                $call.AddOpts | Should -Be '-p no:cacheprovider -m "not live"' `
                    -Because $product
            }
        }
        $env:PYTEST_ADDOPTS | Should -Be '-p no:cacheprovider'
    }
}

Context 'with a TestResourceKey' {
    It 'runs every test, the ones marked live included' {
        Invoke-ProductStep 'run-integration-tests' $script:Repo @{
            RepoName = $script:Repo
            Keys = @{ TestResourceKey = 'key' }
            SeleniumContract = $false
        } 'device-detection', 'location' *>&1 | Out-Null

        foreach ($product in 'device-detection', 'location') {
            $calls = Get-Calls $product
            $calls.Count | Should -BeGreaterThan 0 -Because $product
            foreach ($call in $calls) {
                $call.AddOpts | Should -Not -Match 'live' -Because $product
            }
        }
    }
}

}

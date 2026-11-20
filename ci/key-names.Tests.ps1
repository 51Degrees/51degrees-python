# Tests that the CI scripts, the tox configurations and the cloud tests read
# each key under its _51DEGREES_ name, and never under an old name.
#
# common-ci exports every _51DEGREES_ secret under its own name before any of
# this repository's scripts run, and fills _51DEGREES_RESOURCE_KEY and
# _51DEGREES_RESOURCE_KEY_51DID from _51DEGREES_RESOURCE_KEY_BESPOKE. It
# downloads every data file with _51DEGREES_LICENSE_KEY, which is the data
# license and not a cloud license. No key reaches a script as an option.

BeforeDiscovery {
    $script:DiscoveryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

BeforeAll {
    $script:Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

    # The variables the scripts read or write, saved before each test and put
    # back after it.
    $script:Saved = @(
        '_51DEGREES_RESOURCE_KEY', '_51DEGREES_RESOURCE_KEY_BESPOKE',
        '_51DEGREES_LICENSE_KEY', 'PAID_RESOURCE_KEY', 'TEMP', 'GITHUB_ENV',
        'GITHUB_JOB', 'PYTEST_ADDOPTS')

    function New-TempFolder {
        $path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        return [IO.Directory]::CreateDirectory($path).FullName
    }

    # A folder laid out like a common-ci checkout, which the product scripts
    # run in. Its python/run-integration-tests.ps1 writes the keys it was run
    # with to seen.json, and its steps/fetch-assets.ps1 writes each call to
    # fetch.json and leaves an empty file for each asset.
    function New-CommonCi {
        $path = New-TempFolder
        $null = [IO.Directory]::CreateDirectory((Join-Path $path 'python'))
        $null = [IO.Directory]::CreateDirectory((Join-Path $path 'steps'))
        Set-Content (Join-Path $path 'python' 'run-integration-tests.ps1') @'
param ([string]$RepoName, [string[]]$Packages, [hashtable]$Keys)
@{
    Resource = $env:_51DEGREES_RESOURCE_KEY
    License = $env:_51DEGREES_LICENSE_KEY
} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot '..' 'seen.json')
$global:LASTEXITCODE = 0
'@
        Set-Content (Join-Path $path 'steps' 'fetch-assets.ps1') @'
param (
    [Parameter(Mandatory)][string[]]$Assets,
    [string]$LicenseKey,
    [string]$DeviceDetection,
    [string]$DeviceDetectionUrl,
    [string]$IpIntelligence,
    [string]$IpIntelligenceUrl,
    [string]$CsvUrl
)
$log = Join-Path $PSScriptRoot '..' 'fetch.json'
$calls = @()
if (Test-Path $log) { $calls = @(Get-Content -Raw $log | ConvertFrom-Json) }
$calls += [pscustomobject]@{
    Assets = @($Assets)
    Old = @($PSBoundParameters.Keys | Where-Object { $_ -notin 'Assets', 'LicenseKey' })
}
ConvertTo-Json -InputObject @($calls) -Depth 4 | Set-Content $log
$null = [IO.Directory]::CreateDirectory((Join-Path $PWD 'assets'))
foreach ($asset in $Assets) { Set-Content -LiteralPath "assets/$asset" '' }
'@
        return $path
    }

    # A copy of one product's CI script in a repository of its own, with the
    # scripts it calls replaced by ones that do nothing, and the folders it
    # writes to.
    function New-ProductRepo([string]$Product, [string]$Script) {
        $repo = New-TempFolder
        $ci = [IO.Directory]::CreateDirectory((Join-Path $repo $Product 'ci')).FullName
        Copy-Item (Join-Path $script:Root $Product 'ci' $Script) $ci
        Set-Content (Join-Path $ci 'report-key-products.ps1') 'param ([string]$ResourceKey)'
        Set-Content (Join-Path $ci 'copy-owid-source.ps1') 'param ([string]$RepoRoot)'
        $null = [IO.Directory]::CreateDirectory((Join-Path $repo 'cxx' 'data' 'device-detection'))
        $null = [IO.Directory]::CreateDirectory((Join-Path $repo 'cxx' 'data' 'ip-intelligence'))
        return Join-Path $repo $Product
    }
}

Describe 'Keys under their _51DEGREES_ names' {

    BeforeEach {
        $script:Before = @{}
        foreach ($name in $script:Saved) {
            $script:Before[$name] = [Environment]::GetEnvironmentVariable($name)
            [Environment]::SetEnvironmentVariable($name, $null)
        }
    }

    AfterEach {
        foreach ($name in $script:Saved) {
            [Environment]::SetEnvironmentVariable($name, $script:Before[$name])
        }
    }

    Describe 'Each product''s run-integration-tests.ps1' {

        BeforeEach {
            $script:CommonCi = New-CommonCi
        }

        AfterEach {
            Remove-Item -Recurse -Force $script:CommonCi
        }

        It 'takes the resource key from _51DEGREES_RESOURCE_KEY_BESPOKE in <Product>, with no key option' -ForEach @(
            @{ Product = 'device-detection'; Extra = @{ SeleniumContract = $false } }
            @{ Product = 'ip-intelligence'; Extra = @{} }
            @{ Product = 'location'; Extra = @{} }
            @{ Product = 'pipeline'; Extra = @{} }
        ) {
            $repoName = New-ProductRepo $Product 'run-integration-tests.ps1'
            $env:_51DEGREES_RESOURCE_KEY_BESPOKE = 'bespoke-resource-key'
            $env:_51DEGREES_LICENSE_KEY = 'data-license'
            Push-Location $script:CommonCi
            try {
                & (Join-Path $repoName 'ci' 'run-integration-tests.ps1') `
                    -RepoName $repoName -Keys @{} @Extra
            } finally {
                Pop-Location
            }

            $seen = Get-Content -Raw (Join-Path $script:CommonCi 'seen.json') | ConvertFrom-Json
            $seen.Resource | Should -Be 'bespoke-resource-key'
        }

        It 'leaves the data license common-ci exported as it was in <Product>' -ForEach @(
            @{ Product = 'device-detection'; Extra = @{ SeleniumContract = $false } }
            @{ Product = 'ip-intelligence'; Extra = @{} }
            @{ Product = 'location'; Extra = @{} }
            @{ Product = 'pipeline'; Extra = @{} }
        ) {
            $repoName = New-ProductRepo $Product 'run-integration-tests.ps1'
            $env:_51DEGREES_RESOURCE_KEY_BESPOKE = 'bespoke-resource-key'
            $env:_51DEGREES_LICENSE_KEY = 'data-license'
            Push-Location $script:CommonCi
            try {
                # An old key option, as a caller passing every secret might, must
                # change nothing.
                & (Join-Path $repoName 'ci' 'run-integration-tests.ps1') `
                    -RepoName $repoName -Keys @{ DeviceDetection = 'old-license'; TestResourceKey = 'old-key' } @Extra
            } finally {
                Pop-Location
            }

            $seen = Get-Content -Raw (Join-Path $script:CommonCi 'seen.json') | ConvertFrom-Json
            $seen.License | Should -Be 'data-license'
            $seen.Resource | Should -Be 'bespoke-resource-key'
        }

        It 'fails naming _51DEGREES_RESOURCE_KEY_BESPOKE when it is not set in <Product>' -ForEach @(
            @{ Product = 'device-detection'; Extra = @{ SeleniumContract = $false } }
            @{ Product = 'ip-intelligence'; Extra = @{} }
            @{ Product = 'location'; Extra = @{} }
            @{ Product = 'pipeline'; Extra = @{} }
        ) {
            $repoName = New-ProductRepo $Product 'run-integration-tests.ps1'
            Push-Location $script:CommonCi
            try {
                { & (Join-Path $repoName 'ci' 'run-integration-tests.ps1') `
                    -RepoName $repoName -Keys @{} @Extra } |
                    Should -Throw '*_51DEGREES_RESOURCE_KEY_BESPOKE*'
            } finally {
                Pop-Location
            }
        }
    }

    Describe 'Each product''s fetch-assets.ps1' {

        BeforeEach {
            $script:CommonCi = New-CommonCi
            # The scripts make symbolic links, which need a privilege a test
            # run may not have, and folders for them. Where they point is not
            # what these tests check, so New-Item does nothing here, and the
            # helpers above make their folders without it.
            Mock New-Item { }
        }

        AfterEach {
            Remove-Item -Recurse -Force $script:CommonCi
        }

        It 'takes no key or address option in <Script>' -ForEach @(
            @{ Script = 'ci/fetch-assets.ps1' }
            @{ Script = 'device-detection/ci/fetch-assets.ps1' }
            @{ Script = 'ip-intelligence/ci/fetch-assets.ps1' }
        ) {
            $parameters = (Get-Command (Join-Path $script:Root $Script)).Parameters.Keys
            $parameters | Should -Not -Contain 'DeviceDetection'
            $parameters | Should -Not -Contain 'IpIntelligence'
            $parameters | Should -Not -Contain 'IpIntelligenceUrl'
        }

        It 'asks common-ci for the TAC data file and the CSV with no key option, in device-detection' {
            $repoName = New-ProductRepo 'device-detection' 'fetch-assets.ps1'
            Push-Location $script:CommonCi
            try {
                & (Join-Path $repoName 'ci' 'fetch-assets.ps1')
            } finally {
                Pop-Location
            }

            $calls = @(Get-Content -Raw (Join-Path $script:CommonCi 'fetch.json') | ConvertFrom-Json)
            $calls.Assets | Should -Contain 'TAC-HashV41.hash'
            $calls.Assets | Should -Contain '51Degrees.csv'
            @($calls.Old | Where-Object { $_ }) | Should -BeNullOrEmpty
        }

        It 'asks common-ci for the Enterprise data file with no key or address, and points the tests at it, in ip-intelligence' {
            $repoName = New-ProductRepo 'ip-intelligence' 'fetch-assets.ps1'
            $env:GITHUB_ENV = Join-Path $script:CommonCi 'github.env'
            Push-Location $script:CommonCi
            try {
                & (Join-Path $repoName 'ci' 'fetch-assets.ps1')
            } finally {
                Pop-Location
            }

            $calls = @(Get-Content -Raw (Join-Path $script:CommonCi 'fetch.json') | ConvertFrom-Json)
            $calls.Assets | Should -Contain '51Degrees-EnterpriseIpiV41.ipi'
            @($calls.Old | Where-Object { $_ }) | Should -BeNullOrEmpty
            Get-Content $env:GITHUB_ENV | Should -Match '^_51DEGREES_IPI_PATH=.*51Degrees-EnterpriseIpiV41\.ipi$'
        }
    }

    Describe 'The CI scripts' {

        It 'read no key under an old name in <Path>' -ForEach @(
            Get-ChildItem $script:DiscoveryRoot -Recurse -Filter *.ps1 |
                Where-Object {
                    $_.FullName -match '[\\/]ci[\\/]' -and
                    $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv|\.virtualenv)[\\/]' -and
                    $_.Name -notlike '*.Tests.ps1'
                } |
                ForEach-Object { @{ Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName); Full = $_.FullName } }
        ) {
            $text = Get-Content -Raw $Full
            $text | Should -Not -Match 'TestResourceKey'
            $text | Should -Not -Match '\$Keys\.(DeviceDetection|IpIntelligence)'
            $text | Should -Not -Match '-(DeviceDetection|IpIntelligence|IpIntelligenceUrl)\b'
        }
    }

    Describe 'Each tox.ini' {

        # Every _51DEGREES_ name the package's code or tests name, and the
        # pass_env entries of its tox.ini, which tox matches as patterns.
        It 'passes every _51DEGREES_ variable its package reads, in <Path>' -ForEach @(
            Get-ChildItem $script:DiscoveryRoot -Recurse -Filter tox.ini |
                Where-Object { $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv)[\\/]' } |
                ForEach-Object { @{ Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName); Full = $_.FullName } }
        ) {
            $folder = Split-Path $Full -Parent
            # A folder below with its own tox.ini is its own package.
            $nested = @(Get-ChildItem $folder -Recurse -Filter tox.ini |
                Where-Object { $_.FullName -ne $Full } |
                ForEach-Object { Split-Path $_.FullName -Parent })
            $names = @(Get-ChildItem $folder -Recurse -Filter *.py |
                Where-Object {
                    $file = $_.FullName
                    $file -notmatch '[\\/](\.tox|\.venv|\.virtualenv|build)[\\/]' -and
                    -not ($nested | Where-Object { $file.StartsWith($_ + [IO.Path]::DirectorySeparatorChar) })
                } |
                Select-String -Pattern '(?<![A-Za-z0-9])_51DEGREES_[A-Z0-9_]*[A-Z0-9]' -AllMatches -CaseSensitive |
                ForEach-Object { $_.Matches.Value } |
                Sort-Object -Unique)

            $passed = @()
            $inPassEnv = $false
            foreach ($line in Get-Content $Full) {
                if ($line -match '^\s*\[') { $inPassEnv = $false; continue }
                if ($line -match '^pass_?env\s*=\s*(.*)$') {
                    $inPassEnv = $true
                    $passed += @($Matches[1] -split '[\s,]+' | Where-Object { $_ })
                    continue
                }
                if ($inPassEnv) {
                    if ($line -match '^\S') { $inPassEnv = $false; continue }
                    $entry = ($line -replace '#.*$', '').Trim()
                    if ($entry) { $passed += $entry }
                }
            }

            $missing = @($names | Where-Object {
                $name = $_
                -not ($passed | Where-Object { $name -like $_ })
            })
            $missing | Should -BeNullOrEmpty -Because "tox gives the tests only the variables its pass_env names"
        }
    }

    Describe 'The cloud tests' {

        It 'reads the cloud license from _51DEGREES_LICENSE_KEY_BESPOKE, not the data license, in <Path>' -ForEach @(
            @{ Path = 'pipeline/fiftyone_pipeline_cloudrequestengine/tests/test_licensekey_live.py' }
            @{ Path = 'pipeline/fiftyone_pipeline_cloudrequestengine/examples/tests/helpers.py' }
        ) {
            $text = Get-Content -Raw (Join-Path $script:Root $Path)
            $text | Should -Match '"_51DEGREES_LICENSE_KEY_BESPOKE"'
            $text | Should -Not -Match '"_51DEGREES_LICENSE_KEY"'
            $text | Should -Not -Match 'get_license_key|LICENSE_KEY_ENV_VAR'
        }

        It 'reads the 51Did keys from _51DEGREES_RESOURCE_KEY_51DID and _51DEGREES_LICENSE_KEY_51DID in the 51Did live test' {
            $text = Get-Content -Raw (Join-Path $script:Root 'pipeline/fiftyone_pipeline_did/tests/test_did_client_live.py')
            $text | Should -Match '"_51DEGREES_RESOURCE_KEY_51DID"'
            $text | Should -Match '"_51DEGREES_LICENSE_KEY_51DID"'
            $text | Should -Not -Match '"_51DEGREES_LICENSE_KEY"'
            $text | Should -Not -Match 'find_resource_key\(\)'
        }

        It 'are not given another key under _51DEGREES_LICENSE_KEY or _51DEGREES_RESOURCE_KEY by the Cloud 51Did workflow' {
            $text = Get-Content -Raw (Join-Path $script:Root '.github/workflows/cloud-51did.yml')
            $text | Should -Not -Match '\$env:_51DEGREES_LICENSE_KEY\s*='
            $text | Should -Not -Match '\$env:_51DEGREES_RESOURCE_KEY\s*='
        }
    }
}

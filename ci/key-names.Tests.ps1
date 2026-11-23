# Tests that the CI scripts, the tox configurations and the cloud tests read
# each key under its _51DEGREES_ name, and fill no name from another.
#
# common-ci exports every _51DEGREES_ secret and organization variable under
# its own name before any of this repository's scripts run. The resource
# keys and the license keys are organization secrets.
# The tests that need every property read _51DEGREES_RESOURCE_KEY_BESPOKE.
# _51DEGREES_RESOURCE_KEY is the name a person running an example sets, and
# only an example's own test sets it, for that example. The Cloud 51Did
# workflow takes _51DEGREES_RESOURCE_KEY_51DID and
# _51DEGREES_RESOURCE_KEY_BASIC from the organization secret of the same
# name. It
# downloads every data file with _51DEGREES_LICENSE_KEY, which is the data
# license and not a cloud license. No key reaches a script as an option.
#
# Two names only CI uses have no _51DEGREES_ prefix. CLOUD_STAGING_ENDPOINT,
# an organization variable, names the staging cloud, and
# RESOURCE_KEY_BESPOKE_STAGING, an organization secret, is a Bespoke key it
# knows. Only the Cloud Human Confidence workflow sets them, for the tests
# marked staging, which check what the production cloud does not serve yet.

BeforeDiscovery {
    $script:DiscoveryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

BeforeAll {
    $script:Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

    # The variables the scripts read or write, saved before each test and put
    # back after it.
    $script:Saved = @(
        '_51DEGREES_RESOURCE_KEY', '_51DEGREES_RESOURCE_KEY_BESPOKE',
        '_51DEGREES_LICENSE_KEY', 'TEMP', 'GITHUB_ENV',
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
param ([string]$RepoName, [string[]]$Packages)
@{
    Resource = $env:_51DEGREES_RESOURCE_KEY_BESPOKE
    Example = $env:_51DEGREES_RESOURCE_KEY
    License = $env:_51DEGREES_LICENSE_KEY
} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot '..' 'seen.json')
$global:LASTEXITCODE = 0
'@
        Set-Content (Join-Path $path 'steps' 'fetch-assets.ps1') @'
param (
    [Parameter(Mandatory)][string[]]$Assets,
    [Parameter(ValueFromRemainingArguments)][object[]]$Others
)
$log = Join-Path $PSScriptRoot '..' 'fetch.json'
$calls = @()
if (Test-Path $log) { $calls = @(Get-Content -Raw $log | ConvertFrom-Json) }
$calls += [pscustomobject]@{
    Assets = @($Assets)
    Others = @($Others | ForEach-Object { "$_" })
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

    # The run script of the step called $Step in the workflow file $Workflow,
    # without its indent.
    function Get-StepScript([string]$Workflow, [string]$Step) {
        $lines = @(Get-Content (Join-Path $script:Root '.github/workflows' $Workflow))
        $name = ($lines | Select-String -SimpleMatch "- name: $Step" |
            Select-Object -First 1).LineNumber
        $start = $lines | Select-Object -Skip $name |
            Select-String -Pattern '^(\s*)run: \|\s*$' | Select-Object -First 1
        $indent = $start.Matches[0].Groups[1].Value.Length
        foreach ($line in $lines[($name + $start.LineNumber)..($lines.Count - 1)]) {
            if ($line.Trim() -and $line -notmatch "^\s{$($indent + 1),}") { break }
            if ($line.Length -gt $indent + 2) { $line.Substring($indent + 2) } else { '' }
        }
    }

    # Runs the Cloud Human Confidence workflow's test step in its own process
    # and folder, with the names given set and no others, and python replaced
    # by a function that writes $Report as the junit report and exits with
    # $PytestExitCode. Gives the step's exit code and the output.
    function Invoke-StagingStep([hashtable]$Names, [string]$Report,
            [int]$PytestExitCode = 0) {
        $folder = Join-Path $TestDrive ([Guid]::NewGuid().ToString())
        $null = New-Item -ItemType Directory $folder
        $stepFile = Join-Path $folder 'step.ps1'
        $python = @(
            'function python {'
            '    Write-Output "pytest ran"'
            '    $path = "$($args | Where-Object { "$_" -like "--junit-xml=*" })" -replace "^--junit-xml=", ""'
            "    if (`$path) { Set-Content `$path '$Report' }"
            "    `$global:LASTEXITCODE = $PytestExitCode"
            '}'
        )
        @($python + @(Get-StepScript 'cloud-human-confidence.yml' 'Human Confidence tests against the staging cloud')) |
            Set-Content $stepFile
        $all = 'CLOUD_STAGING_ENDPOINT', 'RESOURCE_KEY_BESPOKE_STAGING',
            '_51DEGREES_RESOURCE_KEY_BASIC'
        $saved = @{}
        foreach ($name in $all) {
            $saved[$name] = [Environment]::GetEnvironmentVariable($name)
            [Environment]::SetEnvironmentVariable($name, $Names[$name])
        }
        Push-Location $folder
        try {
            $output = & (Get-Process -Id $PID).Path -NoProfile -File $stepFile 2>&1 | Out-String
            return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = $output }
        } finally {
            Pop-Location
            foreach ($name in $all) {
                [Environment]::SetEnvironmentVariable($name, $saved[$name])
            }
        }
    }

    # Every name the staging step needs, set to a stand-in.
    $script:StagingNames = @{
        CLOUD_STAGING_ENDPOINT = 'https://cloud.example.test/api/v4/'
        RESOURCE_KEY_BESPOKE_STAGING = 'staging-bespoke-key'
        _51DEGREES_RESOURCE_KEY_BASIC = 'basic-key'
    }

    # A junit report of the two staging tests, as pytest writes it.
    function New-JunitReport([int]$Tests, [int]$Skipped) {
        $cases = for ($i = 0; $i -lt $Tests; $i++) {
            if ($i -lt $Skipped) {
                "<testcase classname=`"t`" name=`"test_$i`"><skipped type=`"pytest.skip`" message=`"CLOUD_STAGING_ENDPOINT is not set.`" /></testcase>"
            } else {
                "<testcase classname=`"t`" name=`"test_$i`" />"
            }
        }
        return ('<?xml version="1.0" encoding="utf-8"?><testsuites>' +
            "<testsuite name=`"pytest`" errors=`"0`" failures=`"0`" " +
            "skipped=`"$Skipped`" tests=`"$Tests`">$($cases -join '')" +
            '</testsuite></testsuites>')
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

        It 'leaves the resource key under _51DEGREES_RESOURCE_KEY_BESPOKE in <Product>, and gives the tests no other name for it' -ForEach @(
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
                    -RepoName $repoName @Extra
            } finally {
                Pop-Location
            }

            $seen = Get-Content -Raw (Join-Path $script:CommonCi 'seen.json') | ConvertFrom-Json
            $seen.Resource | Should -Be 'bespoke-resource-key'
            $seen.Example | Should -BeNullOrEmpty
            $env:_51DEGREES_RESOURCE_KEY | Should -BeNullOrEmpty
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
                & (Join-Path $repoName 'ci' 'run-integration-tests.ps1') `
                    -RepoName $repoName @Extra
            } finally {
                Pop-Location
            }

            $seen = Get-Content -Raw (Join-Path $script:CommonCi 'seen.json') | ConvertFrom-Json
            $seen.License | Should -Be 'data-license'
            $seen.Resource | Should -Be 'bespoke-resource-key'
        }

        It 'runs the tests that need no key, naming _51DEGREES_RESOURCE_KEY_BESPOKE, when it is not set in <Product>' -ForEach @(
            @{ Product = 'device-detection'; Extra = @{ SeleniumContract = $false } }
            @{ Product = 'ip-intelligence'; Extra = @{} }
            @{ Product = 'location'; Extra = @{} }
            @{ Product = 'pipeline'; Extra = @{} }
        ) {
            $repoName = New-ProductRepo $Product 'run-integration-tests.ps1'
            Push-Location $script:CommonCi
            try {
                $output = & (Join-Path $repoName 'ci' 'run-integration-tests.ps1') `
                    -RepoName $repoName @Extra *>&1 | Out-String
            } finally {
                Pop-Location
            }

            $output | Should -Match '_51DEGREES_RESOURCE_KEY_BESPOKE is not set'
            Join-Path $script:CommonCi 'seen.json' | Should -Exist
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
            $parameters = @((Get-Command (Join-Path $script:Root $Script)).Parameters.Keys)
            $parameters | Where-Object { $_ -match 'Key|License|Url' } |
                Should -BeNullOrEmpty
        }

        It 'asks common-ci for the TAC data file and the property CSV with no key option, in device-detection' {
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
            $calls.Assets | Should -Contain '20000 Evidence Records.yml'
            # The evidence is the YAML file, and the only CSV is the
            # property CSV.
            @($calls.Assets | Where-Object {
                    $_ -notmatch '\.(hash|yml)$' -and $_ -ne '51Degrees.csv' }) |
                Should -BeNullOrEmpty
            @($calls.Others | Where-Object { $_ }) | Should -BeNullOrEmpty
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
            @($calls.Others | Where-Object { $_ }) | Should -BeNullOrEmpty
            Get-Content $env:GITHUB_ENV | Should -Match '^_51DEGREES_IPI_PATH=.*51Degrees-EnterpriseIpiV41\.ipi$'
        }
    }

    Describe 'The CI scripts' {

        It 'read no key from the secrets passed to them, and pass none on to the asset download, in <Path>' -ForEach @(
            Get-ChildItem $script:DiscoveryRoot -Recurse -Filter *.ps1 |
                Where-Object {
                    $_.FullName -match '[\\/]ci[\\/]' -and
                    $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv|\.virtualenv)[\\/]' -and
                    $_.Name -notlike '*.Tests.ps1'
                } |
                ForEach-Object { @{ Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName); Full = $_.FullName } }
        ) {
            $text = Get-Content -Raw $Full
            $text | Should -Not -Match '\$Keys\s*(\.|\[)'
            $text | Should -Not -Match 'fetch-assets\.ps1[^\r\n]*\s-(?!Assets\b)[A-Za-z]'
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

        # The 51Did license key unseals only results made with the resource
        # key of its own account. Filled from the Bespoke key, the licensed
        # redeem comes back unreadable.
        It 'are given _51DEGREES_RESOURCE_KEY_51DID from the organization secret of the same name by every workflow' {
            $lines = @(Get-ChildItem (Join-Path $script:Root '.github/workflows') -Filter *.yml |
                Select-String -Pattern '^\s*_51DEGREES_RESOURCE_KEY_51DID\s*:' |
                ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" })
            $lines | Should -Not -BeNullOrEmpty
            $lines | Where-Object {
                $_ -notmatch ':\s*\$\{\{\s*secrets\._51DEGREES_RESOURCE_KEY_51DID\s*\}\}\s*$'
            } | Should -BeNullOrEmpty
        }

        # The Basic tier tests need a key on CloudV5Basic alone. Filled from
        # the FREE key, test_non_marketing_usage_gets_a_51did failed.
        It 'are given _51DEGREES_RESOURCE_KEY_BASIC from the organization secret of the same name by every workflow' {
            $lines = @(Get-ChildItem (Join-Path $script:Root '.github/workflows') -Filter *.yml |
                Select-String -Pattern '^\s*_51DEGREES_RESOURCE_KEY_BASIC\s*:' |
                ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" })
            $lines | Should -Not -BeNullOrEmpty
            $lines | Where-Object {
                $_ -notmatch ':\s*\$\{\{\s*secrets\._51DEGREES_RESOURCE_KEY_BASIC\s*\}\}\s*$'
            } | Should -BeNullOrEmpty
        }

        # Every resource key is an organization secret, so no workflow reads a
        # _51DEGREES_RESOURCE_KEY name as an organization variable.
        It 'read no _51DEGREES_RESOURCE_KEY name as an organization variable in any workflow' {
            @(Get-ChildItem (Join-Path $script:Root '.github/workflows') -Include *.yml, *.yaml -Recurse |
                Select-String -Pattern '\bvars\s*(\.|\[\s*.)_51DEGREES_RESOURCE_KEY' |
                ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" }) |
                Should -BeNullOrEmpty
        }

        It 'are not given another key under _51DEGREES_LICENSE_KEY or _51DEGREES_RESOURCE_KEY by the Cloud 51Did workflow' {
            $text = Get-Content -Raw (Join-Path $script:Root '.github/workflows/cloud-51did.yml')
            $text | Should -Not -Match '\$env:_51DEGREES_LICENSE_KEY\s*='
            $text | Should -Not -Match '\$env:_51DEGREES_RESOURCE_KEY\s*='
        }

        # With the license key set and the _51DEGREES_RESOURCE_KEY_51DID
        # variable missing, the licensed redeem would never run and the job
        # would still pass. So the step fails, naming the missing variable. The
        # step's script runs in its own process, with tox replaced by a
        # function that records it was called.
        It 'fail the Cloud 51Did step, naming _51DEGREES_RESOURCE_KEY_51DID, when only the 51Did license key is set' {
            $lines = @(Get-Content (Join-Path $script:Root '.github/workflows/cloud-51did.yml'))
            $name = ($lines | Select-String -Pattern '^\s*- name: Cloud 51Did test\s*$' |
                Select-Object -First 1).LineNumber
            $start = $lines | Select-Object -Skip $name |
                Select-String -Pattern '^(\s*)run: \|\s*$' | Select-Object -First 1
            $indent = $start.Matches[0].Groups[1].Value.Length
            $body = foreach ($line in $lines[($name + $start.LineNumber)..($lines.Count - 1)]) {
                if ($line.Trim() -and $line -notmatch "^\s{$($indent + 1),}") { break }
                if ($line.Length -gt $indent + 2) { $line.Substring($indent + 2) } else { '' }
            }
            $stepFile = Join-Path $TestDrive 'cloud-51did-step.ps1'
            @(
                "function tox { Write-Output 'tox ran'; `$global:LASTEXITCODE = 0 }"
                $body
            ) | Set-Content $stepFile

            $saved = @(Get-ChildItem env: | Where-Object { $_.Name -like '_51DEGREES_*' })
            try {
                $saved | ForEach-Object { Remove-Item "Env:$($_.Name)" }
                $env:_51DEGREES_LICENSE_KEY_51DID = 'license-51did'
                $output = & (Get-Process -Id $PID).Path -NoProfile -File $stepFile 2>&1 | Out-String
                $exitCode = $LASTEXITCODE
            } finally {
                Get-ChildItem env: | Where-Object { $_.Name -like '_51DEGREES_*' } |
                    ForEach-Object { Remove-Item "Env:$($_.Name)" }
                $saved | ForEach-Object { Set-Item "Env:$($_.Name)" $_.Value }
            }

            $exitCode | Should -Not -Be 0
            $output | Should -Match '_51DEGREES_RESOURCE_KEY_51DID'
            $output | Should -Not -Match 'tox ran'
        }

        # Only the workflow that runs the tests marked staging sets the
        # staging names, so no other workflow's tests call the staging cloud.
        It 'are given <Variable> from the organization <Kind> of the same name by the Cloud Human Confidence workflow alone' -ForEach @(
            @{ Variable = 'CLOUD_STAGING_ENDPOINT'; Kind = 'variable'; Context = 'vars' }
            @{ Variable = 'RESOURCE_KEY_BESPOKE_STAGING'; Kind = 'secret'; Context = 'secrets' }
        ) {
            $lines = @(Get-ChildItem (Join-Path $script:Root '.github/workflows') -Include *.yml, *.yaml -Recurse |
                Select-String -Pattern "\b$Variable\b" |
                Where-Object { $_.Line.Trim() -notmatch '^#' } |
                ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" })
            $lines | Where-Object { $_ -notmatch '^cloud-human-confidence\.yml:' } |
                Should -BeNullOrEmpty
            $given = @($lines | Where-Object { $_ -match ":\s*$Variable\s*:" })
            $given.Count | Should -Be 1
            $given[0] | Should -Match ":\s*$Variable\s*:\s*\$\{\{\s*$Context\.$Variable\s*\}\}\s*$"
        }

        It 'read the staging cloud and its key from CLOUD_STAGING_ENDPOINT and RESOURCE_KEY_BESPOKE_STAGING in the Human Confidence live test' {
            $text = Get-Content -Raw (Join-Path $script:Root 'pipeline/fiftyone_pipeline_cloudrequestengine/examples/tests/test_cloud_humanconfidence_web.py')
            $text | Should -Match '"CLOUD_STAGING_ENDPOINT"'
            $text | Should -Match '"RESOURCE_KEY_BESPOKE_STAGING"'
            $text | Should -Match '@pytest\.mark\.staging'
        }

        It 'fail the Cloud Human Confidence step, naming <Missing>, when it is empty, before any test runs' -ForEach @(
            @{ Missing = 'CLOUD_STAGING_ENDPOINT' }
            @{ Missing = 'RESOURCE_KEY_BESPOKE_STAGING' }
            @{ Missing = '_51DEGREES_RESOURCE_KEY_BASIC' }
        ) {
            $names = $script:StagingNames.Clone()
            $names[$Missing] = $null
            $result = Invoke-StagingStep $names (New-JunitReport 2 0)

            $result.ExitCode | Should -Not -Be 0
            $result.Output | Should -Match "$Missing is empty or missing"
            $result.Output | Should -Not -Match 'pytest ran'
        }

        It 'fail the Cloud Human Confidence step when a staging test skipped' {
            $result = Invoke-StagingStep $script:StagingNames (New-JunitReport 2 1)

            $result.ExitCode | Should -Not -Be 0
            $result.Output | Should -Match 'pytest ran'
            $result.Output | Should -Match 'test_0 skipped'
        }

        # pytest exits 5 when it selects no test, and still writes the report.
        It 'fail the Cloud Human Confidence step when no staging test ran' {
            $result = Invoke-StagingStep $script:StagingNames (New-JunitReport 0 0) 5

            $result.ExitCode | Should -Not -Be 0
            $result.Output | Should -Match 'pytest ran'
            $result.Output | Should -Match 'No staging test ran'
        }

        It 'fail the Cloud Human Confidence step with pytest''s exit code when a staging test failed' {
            $result = Invoke-StagingStep $script:StagingNames (New-JunitReport 2 0) 1

            $result.ExitCode | Should -Be 1
            $result.Output | Should -Not -Match 'No staging test ran'
        }

        It 'pass the Cloud Human Confidence step when every staging test ran' {
            $result = Invoke-StagingStep $script:StagingNames (New-JunitReport 2 0)

            $result.ExitCode | Should -Be 0
            $result.Output | Should -Match 'pytest ran'
        }
    }

    Describe 'The live cloud tests' {

        # A live test with no key skips, naming the variable it reads. It
        # never fails for want of a key.
        It 'skip rather than fail without a key in <Path>' -ForEach @(
            Get-ChildItem $script:DiscoveryRoot -Recurse -Filter *.py |
                Where-Object {
                    $_.FullName -match '[\\/]tests[\\/]' -and
                    $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv|\.virtualenv)[\\/]' -and
                    $_.Name -ne 'live_cloud.py'
                } |
                Where-Object { (Get-Content -Raw $_.FullName) -match 'find_resource_key|read_environment\(|get_resource_key\(' } |
                ForEach-Object { @{ Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName); Full = $_.FullName } }
        ) {
            $text = Get-Content -Raw $Full
            $text | Should -Not -MatchExactly '\.fail\(\s*(NO_|no_resource_key)'
            $text | Should -Not -Match 'assertIsNotNone\(\s*self\.resource_key'
            $text | Should -Not -Match 'raise Exception\("To run the cloud tests'
        }

        It 'skips, naming the variable, when <Path> has no key' -ForEach @(
            @{ Path = 'location/tests/test_examples.py' }
            @{ Path = 'device-detection/fiftyone_devicedetection_examples/tests/test_cloudgettingstartedweb.py' }
        ) {
            $text = Get-Content -Raw (Join-Path $script:Root $Path)
            $text | Should -Match 'skip'
            $text | Should -Match 'no_resource_key\('
        }

        It 'says in live_cloud.py that a test without a key skips, in <Path>' -ForEach @(
            Get-ChildItem $script:DiscoveryRoot -Recurse -Filter live_cloud.py |
                Where-Object { $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv)[\\/]' } |
                ForEach-Object { @{ Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName); Full = $_.FullName } }
        ) {
            $text = Get-Content -Raw $Full
            $text | Should -Not -Match 'There is no fallback to a skip'
        }
    }
}

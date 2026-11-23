# Tests that the CI scripts fit the common-ci scripts they call and are
# called by.
#
# common-ci runs each step script through steps/run-script.ps1, which gives a
# script only the options it declares. The keys are not among the options:
# each is in the environment under its own name before any script runs. So a
# step script declares no Keys parameter, and gives a common-ci script only
# the parameters that script declares.

BeforeDiscovery {
    $script:DiscoveryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

    # Every CI script of this repository, the tests and the copies in the
    # submodule and the virtual environments left out.
    $script:Scripts = @(Get-ChildItem $script:DiscoveryRoot -Recurse -Filter *.ps1 |
        Where-Object {
            $_.FullName -match '[\\/]ci[\\/]' -and
            $_.FullName -notmatch '[\\/](cxx|\.tox|\.venv|\.virtualenv)[\\/]' -and
            $_.Name -notlike '*.Tests.ps1'
        } |
        ForEach-Object { @{
            Path = [IO.Path]::GetRelativePath($script:DiscoveryRoot, $_.FullName)
            Full = $_.FullName
        } })
}

BeforeAll {
    . (Join-Path $PSScriptRoot 'dispatch.ps1')

    # common-ci checked out beside this repository, or wherever
    # _51DEGREES_COMMON_CI_DIR says.
    $commonCi = $env:_51DEGREES_COMMON_CI_DIR
    if ([string]::IsNullOrEmpty($commonCi) -eq $true) {
        $commonCi = Join-Path $PSScriptRoot '..' '..' 'common-ci'
    }
    if ((Test-Path (Join-Path $commonCi 'steps' 'run-script.ps1')) -eq $false) {
        throw "common-ci not found at '$commonCi'; set _51DEGREES_COMMON_CI_DIR to a checkout of it"
    }
    $script:CommonCiSource = (Resolve-Path $commonCi).Path
    $script:Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

    # The calls a script makes to a common-ci script, each with the named
    # parameters it gives.
    function Get-CommonCiCalls([string]$Path) {
        $ast = [Management.Automation.Language.Parser]::ParseFile(
            $Path, [ref]$null, [ref]$null)
        $commands = $ast.FindAll({ param ($node)
                $node -is [Management.Automation.Language.CommandAst] }, $true)
        foreach ($command in $commands) {
            $name = $command.GetCommandName()
            if ($name -notmatch '^\./(python|steps)/[^/]+\.ps1$') {
                continue
            }
            [pscustomobject]@{
                Script = $name.Substring(2)
                Line = $command.Extent.StartLineNumber
                Parameters = @($command.CommandElements |
                    Where-Object { $_ -is [Management.Automation.Language.CommandParameterAst] } |
                    ForEach-Object ParameterName)
            }
        }
    }
}

Describe 'The CI scripts and common-ci' {

    It 'declares no Keys parameter in <Path>' -ForEach $script:Scripts {
        (Get-Command $Full).Parameters.ContainsKey('Keys') | Should -BeFalse
    }

    It 'gives a common-ci script only the parameters it declares in <Path>' -ForEach $script:Scripts {
        $unknown = foreach ($call in (Get-CommonCiCalls $Full)) {
            $target = Join-Path $script:CommonCiSource $call.Script
            $target | Should -Exist -Because "line $($call.Line) calls it"
            $declared = (Get-Command $target).Parameters
            foreach ($parameter in $call.Parameters) {
                if ($declared.ContainsKey($parameter) -eq $false) {
                    "line $($call.Line): -$parameter is not a parameter of $($call.Script)"
                }
            }
        }
        $unknown | Should -BeNullOrEmpty
    }
}

Describe 'The integration test step as common-ci runs it' {

    BeforeEach {
        $script:Saved = @{}
        foreach ($name in '_51DEGREES_RESOURCE_KEY', '_51DEGREES_RESOURCE_KEY_BESPOKE',
                'PYTEST_ADDOPTS', 'TEMP') {
            $script:Saved[$name] = [Environment]::GetEnvironmentVariable($name)
        }
        $env:_51DEGREES_RESOURCE_KEY = $null
        $env:_51DEGREES_RESOURCE_KEY_BESPOKE = $null
        $env:PYTEST_ADDOPTS = $null

        # A folder laid out like a common-ci checkout, with this repository
        # inside it under its own name. Its python/run-integration-tests.ps1
        # has the parameters of common-ci's own, runs no tests, and records
        # the product of each call.
        $script:CommonCi = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        $null = New-Item -ItemType Directory -Force (Join-Path $script:CommonCi 'python')
        Copy-Item -Recurse (Join-Path $script:CommonCiSource 'steps') `
            (Join-Path $script:CommonCi 'steps')
        $real = Join-Path $script:CommonCiSource 'python' 'run-integration-tests.ps1'
        $block = [Management.Automation.Language.Parser]::ParseFile(
            $real, [ref]$null, [ref]$null).ParamBlock.Extent.Text
        Set-Content (Join-Path $script:CommonCi 'python' 'run-integration-tests.ps1') @"
$block
Add-Content (Join-Path `$PWD 'calls.txt') (Split-Path `$RepoName -Leaf)
`$global:LASTEXITCODE = 0
"@
        $script:RepoName = Split-Path -Leaf $script:Repo
        $link = Join-Path $script:CommonCi $script:RepoName
        $null = New-Item -ItemType Junction -Path $link -Target $script:Repo -ErrorAction SilentlyContinue
        if ((Test-Path $link) -eq $false) {
            $null = New-Item -ItemType SymbolicLink -Path $link -Target $script:Repo
        }
        Push-Location $script:CommonCi
    }

    AfterEach {
        Pop-Location
        # The link is removed on its own first, so that removing the folder
        # never follows it into this repository.
        (Get-Item (Join-Path $script:CommonCi $script:RepoName)).Delete()
        Remove-Item -Recurse -Force $script:CommonCi
        foreach ($name in $script:Saved.Keys) {
            [Environment]::SetEnvironmentVariable($name, $script:Saved[$name])
        }
    }

    It 'runs every product''s tests from the options of a build, which hold no keys' {
        # The options common-ci builds: an entry of ci/options.json, and the
        # parameters of its build and test script. No branch has this name,
        # so every product counts as changed.
        $options = @{
            Name = 'Ubuntu_Python_3.12'
            Image = 'ubuntu-latest'
            Language = 'python'
            LanguageVersion = '3.12'
            RunPerformance = $true
            PackageRequirement = $true
            RepoName = $script:RepoName
            OrgName = '51Degrees'
            Branch = 'a-branch-that-does-not-exist'
            PullRequestId = '1'
            DryRun = $true
            SkipLiteTests = $false
        }

        ./steps/run-script.ps1 "./$($script:RepoName)/ci/run-integration-tests.ps1" $options *>&1 |
            Out-Null

        $calls = @(Get-Content (Join-Path $script:CommonCi 'calls.txt'))
        foreach ($product in 'device-detection', 'ip-intelligence', 'location', 'pipeline') {
            $calls | Should -Contain $product
        }
    }
}

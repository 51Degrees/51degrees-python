# Tests for ci/dispatch.ps1.
#
# Each test builds a throwaway repository with two products, 'alpha' and
# 'beta', whose ci/ scripts are written by the test, and runs the dispatcher
# from a folder laid out like a common-ci checkout, with common-ci's real
# steps/run-script.ps1, because that is how common-ci calls it.

BeforeAll {
    . (Join-Path $PSScriptRoot 'dispatch.ps1')

    # common-ci checked out beside this repository, or wherever COMMON_CI says.
    $commonCi = $env:COMMON_CI
    if ([string]::IsNullOrEmpty($commonCi) -eq $true) {
        $commonCi = Join-Path $PSScriptRoot '..' '..' 'common-ci'
    }
    $script:RunScript = Join-Path $commonCi 'steps' 'run-script.ps1'
    if ((Test-Path $script:RunScript) -eq $false) {
        throw "common-ci not found at '$commonCi'; set COMMON_CI to a checkout of it"
    }

    # A repository with packages.json naming one package in each product.
    function New-ProductRepo {
        $path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        $null = New-Item -ItemType Directory -Force (Join-Path $path 'ci')
        @(
            @{ Name = 'a'; Product = 'alpha'; Path = 'alpha/a'; DependsOn = @(); Publish = $true }
            @{ Name = 'b'; Product = 'beta'; Path = 'beta/b'; DependsOn = @(); Publish = $true }
        ) | ConvertTo-Json | Set-Content (Join-Path $path 'ci' 'packages.json')
        git init --quiet $path
        git -C $path add -A
        git -C $path -c user.name=test -c user.email=test@example.com `
            commit --quiet -m 'Start'
        return $path
    }

    # Writes a product's ci/<step>.ps1 with the given body, after a param block
    # taking RepoName, as the products' scripts do.
    function Set-ProductStep([string]$Repo, [string]$Product, [string]$Step,
            [string]$Body) {
        $folder = New-Item -ItemType Directory -Force (Join-Path $Repo $Product 'ci')
        Set-Content (Join-Path $folder "$Step.ps1") `
            "param ([Parameter(Mandatory)][string]`$RepoName)`n$Body"
    }

    # A folder laid out like a common-ci checkout, which the dispatcher runs in.
    function New-CommonCi {
        $path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        $steps = New-Item -ItemType Directory -Force (Join-Path $path 'steps')
        Copy-Item $script:RunScript $steps
        return $path
    }
}

Describe 'dispatch.ps1' {

BeforeEach {
    $script:Repo = New-ProductRepo
    $script:CommonCi = New-CommonCi
    Push-Location $script:CommonCi
}

AfterEach {
    Pop-Location
    Remove-Item -Recurse -Force $script:Repo, $script:CommonCi
}

Describe 'Invoke-ProductStep' {
    It 'runs each product''s own script with the product folder as its repository' {
        Set-ProductStep $script:Repo 'alpha' 'build-project' `
            'Set-Content (Join-Path $RepoName "ran.txt") $RepoName'
        Set-ProductStep $script:Repo 'beta' 'build-project' `
            'Set-Content (Join-Path $RepoName "ran.txt") $RepoName'

        Invoke-ProductStep 'build-project' $script:Repo @{ RepoName = $script:Repo }

        Get-Content (Join-Path $script:Repo 'alpha' 'ran.txt') |
            Should -Be (Join-Path $script:Repo 'alpha')
        Get-Content (Join-Path $script:Repo 'beta' 'ran.txt') |
            Should -Be (Join-Path $script:Repo 'beta')
    }

    It 'skips a product that never had the step' {
        Set-ProductStep $script:Repo 'alpha' 'run-unit-tests' 'Write-Output ok'

        $output = Invoke-ProductStep 'run-unit-tests' $script:Repo @{
            RepoName = $script:Repo } | Out-String

        $output | Should -Match 'beta has no run-unit-tests step'
    }

    It 'runs every product even after one fails, then fails the step' {
        Set-ProductStep $script:Repo 'alpha' 'run-unit-tests' 'exit 1'
        Set-ProductStep $script:Repo 'beta' 'run-unit-tests' `
            'Set-Content (Join-Path $RepoName "ran.txt") ok'

        { Invoke-ProductStep 'run-unit-tests' $script:Repo @{
            RepoName = $script:Repo } } | Should -Throw '*failed for: alpha'

        Test-Path (Join-Path $script:Repo 'beta' 'ran.txt') | Should -BeTrue
    }

    It 'moves each product''s test results to where common-ci collects them' {
        $body = '$dir = New-Item -ItemType Directory -Force ' +
            '(Join-Path $RepoName "test-results" "unit"); ' +
            'Set-Content (Join-Path $dir "$(Split-Path $RepoName -Leaf).xml") x'
        Set-ProductStep $script:Repo 'alpha' 'run-unit-tests' $body
        Set-ProductStep $script:Repo 'beta' 'run-unit-tests' $body

        Invoke-ProductStep 'run-unit-tests' $script:Repo @{ RepoName = $script:Repo }

        $unit = Join-Path $script:Repo 'test-results' 'unit'
        Test-Path (Join-Path $unit 'alpha.xml') | Should -BeTrue
        Test-Path (Join-Path $unit 'beta.xml') | Should -BeTrue
        Test-Path (Join-Path $script:Repo 'alpha' 'test-results') | Should -BeFalse
    }

    It 'fetches assets when called without a repository name' {
        # common-ci's prefetch_assets action runs ci/fetch-assets.ps1 directly
        # with only the keys, from the common-ci checkout that holds this
        # repository's folder. It once stopped asking for RepoName.
        Copy-Item (Join-Path $PSScriptRoot 'fetch-assets.ps1'), `
            (Join-Path $PSScriptRoot 'dispatch.ps1'), `
            (Join-Path $PSScriptRoot 'packages.ps1') (Join-Path $script:Repo 'ci')
        $inCommonCi = Join-Path $script:CommonCi (Split-Path -Leaf $script:Repo)
        Move-Item $script:Repo $inCommonCi
        $script:Repo = $inCommonCi
        Set-ProductStep $script:Repo 'alpha' 'fetch-assets' `
            'Set-Content (Join-Path $RepoName "ran.txt") ok'

        & (Join-Path $script:Repo 'ci' 'fetch-assets.ps1')

        Test-Path (Join-Path $script:Repo 'alpha' 'ran.txt') | Should -BeTrue
    }

    It 'passes on only the options a product''s script declares' {
        # common-ci's run-script.ps1 drops what a script does not declare, so
        # a product without a Keys parameter is not broken by being given Keys.
        Set-ProductStep $script:Repo 'alpha' 'run-integration-tests' 'Write-Output ok'
        Set-ProductStep $script:Repo 'beta' 'run-integration-tests' 'Write-Output ok'

        { Invoke-ProductStep 'run-integration-tests' $script:Repo @{
            RepoName = $script:Repo; Keys = @{ TestResourceKey = 'x' } } } |
            Should -Not -Throw
    }
}

}

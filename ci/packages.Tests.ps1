# Tests for ci/packages.ps1.
#
# The selection rules are tested against a small package list written here, so
# a test states exactly which graph it relies on. The release plan reads tags
# and diffs, so those tests build a throwaway git repository. One test reads the
# real packages.json, to catch a typo in a dependency name or a cycle.

BeforeAll {
    . (Join-Path $PSScriptRoot 'packages.ps1')

    function New-Package([string]$Name, [string]$Product, [string]$Path,
            [string[]]$DependsOn = @(), [bool]$Publish = $true,
            [string]$FirstVersion = $null, [string[]]$ExtraPaths = $null) {
        $package = [pscustomobject]@{
            Name = $Name; Product = $Product; Path = $Path
            DependsOn = $DependsOn; Publish = $Publish
            FirstVersion = $FirstVersion
        }
        if ($ExtraPaths) {
            $package | Add-Member ExtraPaths $ExtraPaths
        }
        return $package
    }

    # A cut-down copy of the real graph: two pipeline packages, one device
    # detection package on top of them, a location package that is its whole
    # product folder, a never-released package and an unpublished example.
    $script:Graph = @(
        New-Package 'core' 'pipeline' 'pipeline/core'
        New-Package 'engines' 'pipeline' 'pipeline/engines' @('core')
        New-Package 'did' 'pipeline' 'pipeline/did' -ExtraPaths @('pipeline/owid')
        New-Package 'dd' 'device' 'device/dd' @('engines')
        New-Package 'location' 'location' 'location' @('core')
        New-Package 'ipi' 'ipi' 'ipi/ipi' @('engines') -FirstVersion '4.5.0'
        New-Package 'examples' 'device' 'device/examples' @('dd') -Publish $false
    )

    # A repository with the given files committed and the given tags on that
    # commit. Further commits are made with Add-Commit.
    function New-Repo([string[]]$Files, [string[]]$Tags) {
        $path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        git init --quiet $path
        Add-Commit $path $Files
        foreach ($tag in $Tags) {
            git -C $path tag $tag
        }
        return $path
    }

    function Add-Commit([string]$Repo, [string[]]$Files) {
        foreach ($file in $Files) {
            $full = Join-Path $Repo $file
            $null = New-Item -ItemType Directory -Force (Split-Path $full)
            Add-Content -Path $full -Value ([Guid]::NewGuid())
        }
        git -C $Repo add -A
        git -C $Repo -c user.name=test -c user.email=test@example.com `
            commit --quiet --allow-empty -m 'Change'
    }

    $script:AllFiles = @(
        'pipeline/core/a.py', 'pipeline/engines/a.py', 'pipeline/did/a.py',
        'pipeline/owid/a.py', 'device/dd/a.py', 'device/examples/a.py',
        'location/setup.py', 'ipi/ipi/a.py')
    $script:AllTags = @('core/4.5.38', 'engines/4.5.38', 'did/4.5.38',
        'dd/4.5.96', 'location/4.5.4')
}

Describe 'packages.ps1' {

AfterEach {
    if ($script:Repo -and (Test-Path $script:Repo)) {
        Remove-Item -Recurse -Force $script:Repo
    }
    $script:Repo = $null
}

Describe 'Get-DependentClosure' {
    It 'adds every package that depends on a changed one, through others' {
        $closure = Get-DependentClosure $script:Graph @('core')
        $closure | Sort-Object | Should -Be @(
            'core', 'dd', 'engines', 'examples', 'ipi', 'location')
    }

    It 'adds nothing for a package nothing depends on' {
        Get-DependentClosure $script:Graph @('did') | Should -Be @('did')
    }

    It 'is empty when given nothing' {
        @(Get-DependentClosure $script:Graph @()).Count | Should -Be 0
    }
}

Describe 'Sort-ByDependency' {
    It 'puts every package after the packages it depends on' {
        $order = Sort-ByDependency $script:Graph @('dd', 'engines', 'core')
        $order | Should -Be @('core', 'engines', 'dd')
    }

    It 'ignores dependencies that are not being sorted' {
        Sort-ByDependency $script:Graph @('dd') | Should -Be @('dd')
    }

    It 'refuses a cycle rather than looping' {
        $cycle = @(
            New-Package 'a' 'p' 'p/a' @('b')
            New-Package 'b' 'p' 'p/b' @('a'))
        { Sort-ByDependency $cycle @('a', 'b') } | Should -Throw '*cycle*'
    }
}

Describe 'Resolve-AffectedProducts' {
    It 'tests only the product of a package nothing depends on' {
        Resolve-AffectedProducts $script:Graph @('device/dd/a.py') |
            Should -Be @('device')
    }

    It 'tests every dependent product when a pipeline package changes' {
        Resolve-AffectedProducts $script:Graph @('pipeline/core/a.py') |
            Should -Be @('pipeline', 'device', 'location', 'ipi')
    }

    It 'counts a vendored folder as a change to the package that vendors it' {
        Resolve-AffectedProducts $script:Graph @('pipeline/owid/x.py') |
            Should -Be @('pipeline')
    }

    It 'tests only the product for a change to its own CI or docs' {
        Resolve-AffectedProducts $script:Graph @('device/ci/build.ps1') |
            Should -Be @('device')
    }

    It 'tests everything for a change outside every product' {
        Resolve-AffectedProducts $script:Graph @('ci/packages.ps1') |
            Should -Be @('pipeline', 'device', 'location', 'ipi')
    }

    It 'treats a product that is one package as that package' {
        Resolve-AffectedProducts $script:Graph @('location/setup.py') |
            Should -Be @('location')
    }

    It 'does not take a longer folder name for a product' {
        # 'location' must not claim 'location-extra/...'.
        Resolve-AffectedProducts $script:Graph @('location-extra/x') |
            Should -Be @('pipeline', 'device', 'location', 'ipi')
    }
}

Describe 'Get-ReleasePlan' {
    It 'releases nothing but first releases when nothing changed since the tags' {
        $script:Repo = New-Repo $script:AllFiles $script:AllTags
        Add-Commit $script:Repo @()
        $plan = @(Get-ReleasePlan $script:Repo $script:Graph)
        $plan.Name | Should -Be @('ipi')
        $plan[0].Version | Should -Be '4.5.0'
        $plan[0].Reason | Should -Be 'first release'
    }

    It 'releases a changed package at the next patch, and its dependents' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('pipeline/engines/a.py')
        $plan = @(Get-ReleasePlan $script:Repo $script:Graph)
        $plan.Name | Should -Be @('engines', 'dd', 'ipi')
        ($plan | Where-Object Name -eq 'engines').Version | Should -Be '4.5.39'
        ($plan | Where-Object Name -eq 'dd').Version | Should -Be '4.5.97'
        ($plan | Where-Object Name -eq 'dd').Reason |
            Should -Be 'a package it depends on is released'
        ($plan | Where-Object Name -eq 'ipi').Version | Should -Be '4.5.1'
    }

    It 'releases a vendoring package when the vendored folder changes' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('pipeline/owid/a.py')
        @(Get-ReleasePlan $script:Repo $script:Graph).Name | Should -Be @('did')
    }

    It 'releases nothing for a change to an unpublished package' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/examples/a.py')
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
    }

    It 'releases nothing for a change outside every package' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('ci/build.ps1', 'device/docs/a.md')
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
    }

    It 'releases nothing a second time from a commit already released' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/a.py')
        git -C $script:Repo tag 'dd/4.5.97'
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
    }

    It 'continues from the highest tag, not the latest one made' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + @(
            'ipi/4.5.0', 'dd/4.5.9'))
        Add-Commit $script:Repo @('device/dd/a.py')
        (@(Get-ReleasePlan $script:Repo $script:Graph) |
            Where-Object Name -eq 'dd').Version | Should -Be '4.5.97'
    }

    It 'does not read another package''s tags as its own' {
        # 'ipi' must not see tags of a package whose name starts with 'ipi'.
        $graph = $script:Graph + (New-Package 'ipi_cloud' 'ipi' 'ipi/cloud' -FirstVersion '4.5.0')
        $script:Repo = New-Repo ($script:AllFiles + 'ipi/cloud/a.py') (
            $script:AllTags + 'ipi_cloud/4.5.7')
        $plan = @(Get-ReleasePlan $script:Repo $graph)
        ($plan | Where-Object Name -eq 'ipi').Version | Should -Be '4.5.0'
    }

    It 'plans a changed package for a caller that stops on native errors' {
        # publish-package.ps1 stops on a failing native command; 'git diff
        # --quiet' exiting 1 for a changed package once failed the publish.
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/a.py')
        $plan = & {
            $ErrorActionPreference = 'Stop'
            $PSNativeCommandUseErrorActionPreference = $true
            @(Get-ReleasePlan $script:Repo $script:Graph)
        }
        $plan.Name | Should -Be @('dd')
    }

    It 'reads the tags whatever folder it runs from' {
        # PowerShell expands a wildcard in a native command's argument into
        # matching files, so a tag pattern run from a folder that holds a
        # folder of the same name, as the repository root holds 'location',
        # once found no tags.
        $script:Repo = New-Repo $script:AllFiles $script:AllTags
        $here = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
        $null = New-Item -ItemType Directory -Force (Join-Path $here 'location')
        $null = New-Item -ItemType File (Join-Path $here 'location' 'setup.py')
        Push-Location $here
        try {
            (Get-ReleasedVersions $script:Repo 'location')[-1] | Should -Be ([version]'4.5.4')
        } finally {
            Pop-Location
            Remove-Item -Recurse -Force $here
        }
    }

    It 'refuses a never-released package with no FirstVersion' {
        $graph = @(New-Package 'new' 'p' 'p/new')
        $script:Repo = New-Repo @('p/new/a.py') @()
        { Get-ReleasePlan $script:Repo $graph } | Should -Throw '*FirstVersion*'
    }
}

Describe 'the real packages.json' {
    BeforeAll {
        $script:Real = Get-Packages (Split-Path $PSScriptRoot)
    }

    It 'names only packages it defines as dependencies' {
        $names = $script:Real.Name
        foreach ($package in $script:Real) {
            foreach ($dependency in $package.DependsOn) {
                $names | Should -Contain $dependency
            }
        }
    }

    It 'has no dependency cycle' {
        { Sort-ByDependency $script:Real $script:Real.Name } | Should -Not -Throw
    }

    It 'publishes the sixteen PyPI distributions' {
        @($script:Real | Where-Object Publish -eq $true).Count | Should -Be 16
    }

    It 'publishes only the two packages with a C extension as source only' {
        # common-ci builds a wheel for every other package; a wheel of these is
        # tagged for the build machine and PyPI rejects it.
        ($script:Real | Where-Object SourceOnly -eq $true).Name | Sort-Object |
            Should -Be @('fiftyone_devicedetection_onpremise',
                'fiftyone_ipintelligence_onpremise')
    }

    It 'starts every never-tagged IP Intelligence package at 4.5.0' {
        $ipi = @($script:Real | Where-Object {
            $_.Product -eq 'ip-intelligence' -and $_.Publish -eq $true })
        $ipi.Count | Should -Be 5
        $ipi.FirstVersion | Select-Object -Unique | Should -Be '4.5.0'
    }
}

}

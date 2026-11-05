# Tests for ci/packages.ps1.
#
# The selection rules are tested against a small package list written here, so
# a test states exactly which graph it relies on. Some tests read the real
# packages.json, to catch a typo in a dependency name or a cycle. The release
# plan, which packages.ps1 loads from common-ci, is tested there.

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
}

Describe 'packages.ps1' {

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

    It 'has every tox.ini install the packages its package depends on' {
        Get-ToxGaps (Split-Path $PSScriptRoot) $script:Real |
            Should -BeNullOrEmpty
    }
}

}

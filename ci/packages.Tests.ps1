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

    It 'says how many files counted' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/a.py', 'device/dd/b.py')
        (@(Get-ReleasePlan $script:Repo $script:Graph) |
            Where-Object Name -eq 'dd').Reason |
            Should -Be 'changed since 4.5.96 (2 files)'
    }

    It 'releases nothing for a change only to documentation, tests or examples' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @(
            'device/dd/readme.md', 'device/dd/docs/guide.txt',
            'device/dd/tests/test_a.py', 'device/dd/test/a.py',
            'device/dd/examples/a.py', 'device/dd/LICENSE',
            'pipeline/core/sub/notes.md')
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
    }

    It 'ignores documentation, tests and examples whatever their case' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @(
            'device/dd/README.MD', 'device/dd/Tests/a.py',
            'device/dd/Examples/a.py')
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
    }

    It 'releases for the code changed beside the documentation' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/readme.md', 'device/dd/a.py')
        $plan = @(Get-ReleasePlan $script:Repo $script:Graph)
        $plan.Name | Should -Be @('dd')
        $plan[0].Reason | Should -Be 'changed since 4.5.96 (1 file)'
    }

    It 'leaves out the files a package''s Ignore globs match' {
        $graph = @($script:Graph | ForEach-Object { $_.PSObject.Copy() })
        ($graph | Where-Object Name -eq 'dd') |
            Add-Member Ignore @('device/dd/tox.ini')
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/tox.ini')
        @(Get-ReleasePlan $script:Repo $graph).Count | Should -Be 0
    }

    It 'counts documentation for a package that turns the defaults off' {
        $graph = @($script:Graph | ForEach-Object { $_.PSObject.Copy() })
        ($graph | Where-Object Name -eq 'dd') | Add-Member IgnoreDefaults $false
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/readme.md')
        @(Get-ReleasePlan $script:Repo $graph).Name | Should -Be @('dd')
    }
}

Describe 'release-plan-filter.ps1' {
    BeforeAll {
        # A setup.py, setup.cfg and pyproject.toml like the ones here, with
        # the metadata the filter leaves out and settings it does not. Line
        # endings are made LF, whatever the checkout gave this file.
        $script:SetupPy = @'
import setuptools

setuptools.setup(
    name="dd",
    version=read("version.txt"),
    author="51Degrees Engineering",
    author_email="engineering@51degrees.com",
    project_urls={"Source": "https://github.com/51Degrees/51degrees-python"},
    description=("Device detection."),
    keywords=["51degrees", "device-detection"],
    long_description=read("readme.md"),
    long_description_content_type='text/markdown',
    python_requires=">=3.10",
    install_requires=["fiftyone_pipeline_core"],
    classifiers=["Programming Language :: Python"],
)
'@.Replace("`r`n", "`n")
        $script:SetupCfg = @'
[metadata]
name = dd
description = Device detection.
url = https://github.com/51Degrees/51degrees-python

[options]
install_requires =
    fiftyone_pipeline_core
'@.Replace("`r`n", "`n") + "`n"
        $script:Pyproject = @'
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dd"
description = "Device detection."
keywords = [
    "51degrees",
    "device-detection",
]
dependencies = ["fiftyone_pipeline_core"]

[project.urls]
Source = "https://github.com/51Degrees/51degrees-python"
'@.Replace("`r`n", "`n") + "`n"

        # A repository with the given files, holding the filter as this
        # repository does, with the tags of the small graph and the tag of
        # dd on the commit that adds the files.
        function New-FilterRepo([hashtable]$Files) {
            $repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
            $null = New-Item -ItemType Directory -Force (Join-Path $repo 'ci')
            foreach ($name in 'release-plan-filter.ps1', 'release-plan-filter.py') {
                Copy-Item (Join-Path $PSScriptRoot $name) (Join-Path $repo 'ci')
            }
            Set-Files $repo $Files
            git -C $repo tag -f 'dd/4.5.96' | Out-Null
            return $repo
        }

        # Commits the files with exactly the text given.
        function Set-Files([string]$Repo, [hashtable]$Files) {
            foreach ($file in $Files.Keys) {
                $full = Join-Path $Repo $file
                $null = New-Item -ItemType Directory -Force (Split-Path $full)
                [IO.File]::WriteAllText($full, $Files[$file])
            }
            git -C $Repo add -A
            git -C $Repo -c user.name=test -c user.email=test@example.com `
                commit --quiet --allow-empty -m 'Change'
        }

        function Get-DdPlan([string]$Repo) {
            return @(Get-ReleasePlan $Repo $script:Graph |
                Where-Object Name -eq 'dd')
        }
    }

    It 'does not release for a setup.py change only to metadata' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.py' = $script:SetupPy }
        $changed = $script:SetupPy
        $changed = $changed.Replace('Device detection.', 'Device detection for Python.')
        $changed = $changed.Replace('"device-detection"]', '"device-detection", "user-agent"]')
        $changed = $changed.Replace('51degrees-python"}', '51degrees-python", "Docs": "x"}')
        $changed = $changed.Replace('51Degrees Engineering', '51Degrees')
        $changed = $changed.Replace('"Programming Language :: Python"]',
            '"Programming Language :: Python", "Typing :: Typed"]')
        $changed = $changed.Replace("'text/markdown'", "'text/x-rst'")
        Set-Files $script:Repo @{ 'device/dd/setup.py' = $changed + "# A note.`n" }
        (Get-DdPlan $script:Repo).Count | Should -Be 0
    }

    It 'releases for a setup.py change to anything else' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.py' = $script:SetupPy }
        $changed = $script:SetupPy.Replace('["fiftyone_pipeline_core"]',
            '["fiftyone_pipeline_core>=4.5.40"]')
        Set-Files $script:Repo @{ 'device/dd/setup.py' = $changed }
        $plan = Get-DdPlan $script:Repo
        $plan.Count | Should -Be 1
        $plan[0].Reason | Should -Be 'changed since 4.5.96 (1 file)'
    }

    It 'counts the code changed beside a setup.py change only to metadata' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.py' = $script:SetupPy }
        Set-Files $script:Repo @{
            'device/dd/setup.py' = $script:SetupPy.Replace(
                'Device detection.', 'Device detection for Python.')
            'device/dd/src/a.py' = 'print(1)'
        }
        (Get-DdPlan $script:Repo)[0].Reason |
            Should -Be 'changed since 4.5.96 (1 file)'
    }

    It 'does not release for a setup.cfg change only to metadata' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.cfg' = $script:SetupCfg }
        $changed = $script:SetupCfg.Replace('Device detection.', 'Device detection for Python.')
        $changed = $changed.Replace('51degrees-python', '51degrees-python/tree/main')
        Set-Files $script:Repo @{ 'device/dd/setup.cfg' = $changed }
        (Get-DdPlan $script:Repo).Count | Should -Be 0
    }

    It 'releases for a setup.cfg change to its options' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.cfg' = $script:SetupCfg }
        Set-Files $script:Repo @{ 'device/dd/setup.cfg' =
            $script:SetupCfg + "    fiftyone_pipeline_engines`n" }
        (Get-DdPlan $script:Repo).Count | Should -Be 1
    }

    It 'does not release for a pyproject.toml change only to metadata' {
        $script:Repo = New-FilterRepo @{ 'device/dd/pyproject.toml' = $script:Pyproject }
        $changed = $script:Pyproject.Replace('"Device detection."', '"Device detection for Python."')
        $changed = $changed.Replace("    `"device-detection`",`n",
            "    `"device-detection`",`n    `"user-agent`",`n")
        $changed = $changed.Replace('Source = ', "Docs = `"x`"`nSource = ")
        $changed += "`n[[project.authors]]`nname = `"51Degrees`"`n"
        Set-Files $script:Repo @{ 'device/dd/pyproject.toml' = $changed }
        (Get-DdPlan $script:Repo).Count | Should -Be 0
    }

    It 'releases for a pyproject.toml change to <Changed>' -ForEach @(
        @{ Was = '["fiftyone_pipeline_core"]'; Changed = '["fiftyone_pipeline_core>=4.5"]' }
        @{ Was = '"setuptools>=42"'; Changed = '"setuptools>=61"' }
    ) {
        $script:Repo = New-FilterRepo @{ 'device/dd/pyproject.toml' = $script:Pyproject }
        Set-Files $script:Repo @{ 'device/dd/pyproject.toml' =
            $script:Pyproject.Replace($Was, $Changed) }
        (Get-DdPlan $script:Repo).Count | Should -Be 1
    }

    It 'releases for a manifest that is new since the last tag' {
        $script:Repo = New-FilterRepo @{}
        Set-Files $script:Repo @{ 'device/dd/setup.py' = $script:SetupPy }
        (Get-DdPlan $script:Repo).Count | Should -Be 1
    }

    It 'releases for a manifest it cannot read' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.py' = $script:SetupPy }
        Set-Files $script:Repo @{ 'device/dd/setup.py' = 'setup(' }
        (Get-DdPlan $script:Repo).Count | Should -Be 1
    }
}

Describe 'Get-BuildPlan' {
    It 'is the release plan when a package is to be released' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('pipeline/engines/a.py')
        $plan = @(Get-BuildPlan $script:Repo $script:Graph)
        $plan.Name | Should -Be @('engines', 'dd', 'ipi')
        ($plan | Where-Object Name -eq 'engines').Version | Should -Be '4.5.39'
    }

    It 'builds every published package at its released version when nothing changed' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @()
        @(Get-ReleasePlan $script:Repo $script:Graph).Count | Should -Be 0
        $plan = @(Get-BuildPlan $script:Repo $script:Graph)
        $plan.Name | Should -Be @('core', 'did', 'engines', 'location', 'dd', 'ipi')
        ($plan | Where-Object Name -eq 'core').Version | Should -Be '4.5.38'
        ($plan | Where-Object Name -eq 'dd').Version | Should -Be '4.5.96'
        ($plan | Where-Object Name -eq 'location').Version | Should -Be '4.5.4'
        ($plan | Where-Object Name -eq 'ipi').Version | Should -Be '4.5.0'
    }

    It 'builds the released versions from a commit already released' {
        $script:Repo = New-Repo $script:AllFiles ($script:AllTags + 'ipi/4.5.0')
        Add-Commit $script:Repo @('device/dd/a.py')
        git -C $script:Repo tag 'dd/4.5.97'
        ($plan = @(Get-BuildPlan $script:Repo $script:Graph)).Count | Should -Be 6
        ($plan | Where-Object Name -eq 'dd').Version | Should -Be '4.5.97'
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

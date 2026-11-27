# Tests for ci/packages.ps1 and ci/release-plan-filter.ps1.
#
# The selection rules are tested against a small package list written here, so
# a test states exactly which graph it relies on. The release plan, which
# packages.ps1 loads from common-ci, is tested there. The tests of this
# repository's filter and of the build plan read tags and diffs, so they build
# a throwaway git repository. Some tests read the real packages.json, to catch
# a typo in a dependency name or a cycle, and to check its Ignore globs.

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

    It 'does not release for a change only to the maintainers in <Case>' -ForEach @(
        @{ Case = 'setup.py'; File = 'setup.py'; Start = 'SetupPy'
           Was = 'author_email="engineering@51degrees.com",'
           Changed = "author_email=`"engineering@51degrees.com`",`n    maintainer=`"51Degrees`",`n    maintainer_email=`"support@51degrees.com`"," }
        @{ Case = 'setup.cfg'; File = 'setup.cfg'; Start = 'SetupCfg'
           Was = "name = dd`n"
           Changed = "name = dd`nmaintainer = 51Degrees`nmaintainer_email = support@51degrees.com`n" }
        @{ Case = 'a pyproject.toml key'; File = 'pyproject.toml'; Start = 'Pyproject'
           Was = 'dependencies = '
           Changed = "maintainers = [{ name = `"51Degrees`" }]`ndependencies = " }
        @{ Case = 'a pyproject.toml table'; File = 'pyproject.toml'; Start = 'Pyproject'
           Was = '[project.urls]'
           Changed = "[[project.maintainers]]`nname = `"51Degrees`"`n`n[project.urls]" }
    ) {
        $text = @{
            SetupPy = $script:SetupPy
            SetupCfg = $script:SetupCfg
            Pyproject = $script:Pyproject
        }[$Start]
        $changed = $text.Replace($Was, $Changed)
        $changed | Should -Not -Be $text
        $script:Repo = New-FilterRepo @{ "device/dd/$File" = $text }
        Set-Files $script:Repo @{ "device/dd/$File" = $changed }
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

    It 'releases for a manifest that is not UTF-8' {
        $script:Repo = New-FilterRepo @{ 'device/dd/setup.py' = $script:SetupPy }
        [IO.File]::WriteAllBytes((Join-Path $script:Repo 'device/dd/setup.py'),
            [byte[]](0x23, 0xff, 0xfe, 0x0a))
        Set-Files $script:Repo @{}
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

    Context 'a change to a package''s tox.ini' {
        BeforeAll {
            $published = @($script:Real | Where-Object Publish -eq $true)
            $script:RealTags = @($published | ForEach-Object { "$($_.Name)/4.5.1" })
            $script:RealFiles = @($script:Real | ForEach-Object {
                "$($_.Path)/src/a.py"
                "$($_.Path)/tox.ini"
            })
        }

        It 'releases nothing, whichever package it sits beside' {
            $script:Repo = New-Repo $script:RealFiles $script:RealTags
            Add-Commit $script:Repo ($script:Real | ForEach-Object { "$($_.Path)/tox.ini" })
            @(Get-ReleasePlan $script:Repo $script:Real).Count | Should -Be 0
        }

        It 'still releases a package for a change to its source' {
            $script:Repo = New-Repo $script:RealFiles $script:RealTags
            Add-Commit $script:Repo @(
                'pipeline/fiftyone_pipeline_core/tox.ini',
                'pipeline/fiftyone_pipeline_core/src/a.py')
            $plan = @(Get-ReleasePlan $script:Repo $script:Real)
            $plan.Name | Should -Contain 'fiftyone_pipeline_core'
            ($plan | Where-Object Name -eq 'fiftyone_pipeline_core').Reason |
                Should -Be 'changed since 4.5.1 (1 file)'
        }

        It 'is ignored by every package, so one added later counts for nothing' {
            foreach ($package in $script:Real) {
                $package.Ignore | Should -Contain '**/tox.ini' -Because $package.Name
            }
        }
    }
}

}

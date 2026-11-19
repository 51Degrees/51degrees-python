# Tests for ci/write-package-versions.ps1, which writes the version.txt each
# published package's setup.py reads.
#
# Each test copies the script to a throwaway folder beside a packages.ps1
# whose release plan is the one the test gives, so the test states the plan
# it writes from. Two packages stand in for the real ones. engines was last
# released at 4.5.43 and cre at 4.5.44, and cre requires engines>=4.5.44.

Describe 'write-package-versions.ps1' {
    BeforeAll {
        $script:Script = Join-Path $PSScriptRoot 'write-package-versions.ps1'

        # Runs the script on a repository holding engines and cre, with the
        # release plan given as package name to version.
        function Invoke-Write([hashtable]$Plan) {
            $ci = Join-Path $script:Folder 'ci'
            $entries = @($Plan.GetEnumerator() | ForEach-Object {
                "[pscustomobject]@{ Name = '$($_.Key)'; Version = '$($_.Value)' }"
            }) -join ', '
            Set-Content (Join-Path $ci 'packages.ps1') @"
function Get-ReleasePlan(`$RepoPath) { @($entries) }
function Get-Packages(`$RepoPath) {
    @([pscustomobject]@{ Name = 'engines'; Path = 'engines'; Publish = `$true },
        [pscustomobject]@{ Name = 'cre'; Path = 'cre'; Publish = `$true })
}
function Get-ReleasedVersions(`$RepoPath, `$Name) {
    @{ engines = @('4.5.42', '4.5.43'); cre = @('4.5.43', '4.5.44') }[`$Name]
}
"@
            & (Join-Path $ci 'write-package-versions.ps1') -RepoName $script:Repo
        }

        function Get-Written([string]$Name) {
            $file = Join-Path $script:Repo $Name 'version.txt'
            if (Test-Path $file) {
                return (Get-Content $file -Raw).Trim()
            }
            return $null
        }
    }

    BeforeEach {
        $script:Folder = Join-Path ([IO.Path]::GetTempPath()) `
            ([Guid]::NewGuid().ToString())
        $script:Repo = Join-Path $script:Folder 'repo'
        $null = New-Item -ItemType Directory (Join-Path $script:Folder 'ci'),
            (Join-Path $script:Repo 'engines'), (Join-Path $script:Repo 'cre')
        git init --quiet $script:Repo
        Set-Content (Join-Path $script:Repo 'engines' 'setup.py') `
            'install_requires=["requests"]'
        Set-Content (Join-Path $script:Repo 'cre' 'setup.py') `
            'install_requires=["engines>=4.5.44", "requests"]'
        Copy-Item $script:Script (Join-Path $script:Folder 'ci')
    }

    AfterEach {
        Remove-Item -Recurse -Force $script:Folder
    }

    It 'writes the planned versions when the plan releases a dependency at the version required' {
        $null = Invoke-Write @{ engines = '4.5.44'; cre = '4.5.45' }
        Get-Written 'engines' | Should -Be '4.5.44'
        Get-Written 'cre' | Should -Be '4.5.45'
    }

    It 'fails, naming both versions, when the plan leaves out a dependency required above its last release' {
        { Invoke-Write @{ cre = '4.5.45' } } |
            Should -Throw '*engines is required at 4.5.44 or later by cre*last release*4.5.43*'
        Get-Written 'engines' | Should -BeNullOrEmpty
    }

    It 'fails when the plan releases nothing and a requirement is above a last release' {
        { Invoke-Write @{} } |
            Should -Throw '*engines is required at 4.5.44 or later by cre*'
        Get-Written 'engines' | Should -BeNullOrEmpty
    }

    It 'fails when the plan gives a dependency a version below the one required' {
        Set-Content (Join-Path $script:Repo 'cre' 'setup.py') `
            'install_requires=["engines>=4.5.45"]'
        { Invoke-Write @{ engines = '4.5.44'; cre = '4.5.45' } } |
            Should -Throw '*engines is required at 4.5.45 or later by cre*release plan gives it 4.5.44*'
    }
}

# Tests for ci/get-next-package-version.ps1, which labels a publish with the
# highest version in the release plan.
#
# Each test copies the script to a throwaway folder beside a packages.ps1
# whose release plan is the versions the test gives, so the test states the
# plan it labels.

Describe 'get-next-package-version.ps1' {
    BeforeAll {
        $script:Label = Join-Path $PSScriptRoot 'get-next-package-version.ps1'

        function Get-Label([string[]]$Versions) {
            $folder = Join-Path ([IO.Path]::GetTempPath()) `
                ([Guid]::NewGuid().ToString())
            $null = New-Item -ItemType Directory $folder
            try {
                Copy-Item $script:Label $folder
                $list = ($Versions | ForEach-Object { "'$_'" }) -join ', '
                Set-Content (Join-Path $folder 'packages.ps1') @"
function Get-ReleasePlan(`$RepoPath) {
    @(@($list) | ForEach-Object {
        [pscustomobject]@{ Name = "package-`$_"; Version = `$_ }
    })
}
"@
                & (Join-Path $folder 'get-next-package-version.ps1') `
                    -RepoName 'repository' -VariableName 'TestLabel'
                return $global:TestLabel
            } finally {
                Remove-Item -Recurse -Force $folder
            }
        }
    }

    It 'labels a plan of one package with its whole version' {
        Get-Label @('4.5.3') | Should -Be '4.5.3'
    }

    It 'labels a plan of several packages with the highest version' {
        Get-Label @('4.5.3', '4.5.10', '4.5.9') | Should -Be '4.5.10'
    }

    It 'gives a valid version when nothing is released' {
        Get-Label @() | Should -Be '4.5.0'
    }
}

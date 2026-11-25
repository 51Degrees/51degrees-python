# Tests that .github/workflows/free-threaded-python.yml takes the free Lite
# data files from the assets common-ci fetches for each run, in one job, and
# that the jobs that test restore them from that job's cache, rather than any
# job downloading them from the links in the data submodule.
# The workflow is read as text, as the runners have no YAML module.

BeforeAll {
    $script:Workflow = Join-Path $PSScriptRoot '..' '.github' 'workflows' `
        'free-threaded-python.yml'
    $lines = @(Get-Content -LiteralPath $script:Workflow)
    $script:Text = $lines -join "`n"

    # Each job's lines, by the job's name, from the two-space keys under jobs.
    $script:Jobs = [ordered]@{}
    $inJobs = $false
    $name = $null
    foreach ($line in $lines) {
        if ($line -match '^\S') {
            $inJobs = $line -match '^jobs:\s*$'
            $name = $null
            continue
        }
        if (-not $inJobs) { continue }
        if ($line -match '^  ([\w-]+):\s*$') {
            $name = $Matches[1]
            $script:Jobs[$name] = [System.Collections.Generic.List[string]]::new()
            continue
        }
        if ($name) { $script:Jobs[$name].Add($line) }
    }

    # The text of the step that uses the action given, from its "- name:" or
    # "- uses:" line to the next step.
    function Get-Step([string]$Job, [string]$Uses) {
        $steps = @()
        $current = $null
        foreach ($line in $script:Jobs[$Job]) {
            if ($line -match '^      - ') {
                if ($null -ne $current) { $steps += , $current }
                $current = [System.Collections.Generic.List[string]]::new()
            }
            if ($null -ne $current) { $current.Add($line) }
        }
        if ($null -ne $current) { $steps += , $current }
        return @($steps | Where-Object {
                ($_ -join "`n") -match "(?m)uses:\s*$([regex]::Escape($Uses))(@|\s*$)" })
    }

    function Get-Value($Step, [string]$Key) {
        foreach ($line in $Step) {
            if ($line -match "^\s+$Key\:\s*(.+?)\s*$") { return $Matches[1] }
        }
    }

    $script:Fetching = @($script:Jobs.Keys | Where-Object {
            ($script:Jobs[$_] -join "`n") -match 'uses:\s*\S*prefetch_assets' })
    $script:Testing = @($script:Jobs.Keys | Where-Object {
            ($script:Jobs[$_] -join "`n") -match 'pytest' })
}

Describe 'free-threaded-python.yml' {
    It 'never downloads from the links in the data submodule' {
        $script:Text | Should -Not -Match 'get-data-files'
    }

    It 'finds or fetches the assets in one job only' {
        $script:Fetching.Count | Should -Be 1
    }

    It 'names that job Configure, so every product''s assets are fetched' {
        # ci/fetch-assets.ps1 fetches every product's assets only in a job of
        # that name, and the cache it fills is shared with the other
        # workflows.
        $script:Fetching[0] | Should -BeExactly 'Configure'
        Get-Content -Raw (Join-Path $PSScriptRoot 'fetch-assets.ps1') |
            Should -Match "GITHUB_JOB\s+-eq\s+'Configure'"
    }

    It 'fetches with common-ci''s action, run from common-ci''s checkout' {
        $job = $script:Fetching[0]
        $prefetch = @(Get-Step $job './.github/actions/prefetch_assets')
        $prefetch.Count | Should -Be 1
        Get-Value $prefetch[0] 'id' | Should -Not -BeNullOrEmpty
        Get-Value $prefetch[0] 'license-key' | Should -Not -BeNullOrEmpty
        $checkouts = @(Get-Step $job 'actions/checkout')
        @($checkouts | Where-Object {
                (Get-Value $_ 'repository') -eq '51Degrees/common-ci' -and
                -not (Get-Value $_ 'path') }).Count | Should -Be 1
        $own = @($checkouts | Where-Object { -not (Get-Value $_ 'repository') })
        $own.Count | Should -Be 1
        Get-Value $own[0] 'path' | Should -Be (Get-Value $prefetch[0] 'repo')
        Get-Value $own[0] 'submodules' | Should -Be 'recursive'
    }

    It 'gives the cache key to the jobs that test' {
        $job = $script:Fetching[0]
        $id = Get-Value (@(Get-Step $job './.github/actions/prefetch_assets')[0]) 'id'
        ($script:Jobs[$job] -join "`n") | Should -Match (
            '\n    outputs:\s*\n\s+key:\s*' +
            [regex]::Escape('${{ steps.' + $id + '.outputs.cache-key }}'))
    }

    It 'never fetches in a job that runs the tests' {
        $script:Testing.Count | Should -BeGreaterThan 0
        foreach ($job in $script:Testing) {
            $script:Fetching | Should -Not -Contain $job
        }
    }

    It 'restores the assets in each job that runs the tests, as prefetch_assets saves them' {
        $job = $script:Fetching[0]
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            $text | Should -Match "\n    needs:\s*\[?\s*$([regex]::Escape($job))\b"
            $restore = @(Get-Step $testing 'actions/cache/restore')
            $restore.Count | Should -Be 1
            Get-Value $restore[0] 'path' | Should -Be 'assets'
            Get-Value $restore[0] 'key' |
                Should -Be ('${{ needs.' + $job + '.outputs.key }}')
            Get-Value $restore[0] 'fail-on-cache-miss' | Should -Be 'true'
            Get-Value $restore[0] 'enableCrossOsArchive' | Should -Be 'true'
        }
    }

    It 'puts each free data file the tests use in place from the assets' {
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            foreach ($file in '51Degrees-LiteV4.1.hash', '20000 Evidence Records.yml',
                '51Degrees-IPIV4AsnIpiV41.ipi', '51Degrees-LiteIpiV41.ipi') {
                $text | Should -Match ([regex]::Escape("assets/$file"))
            }
            $text | Should -Match ([regex]::Escape('51Degrees-LiteV41.ipi'))
        }
    }

    It 'writes the package versions before it installs the packages from this checkout' {
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            $write = $text.IndexOf('./ci/write-package-versions.ps1')
            $install = $text.IndexOf('-e pipeline/')
            $write | Should -BeGreaterThan -1
            $install | Should -BeGreaterThan $write
        }
    }

    It 'checks out the release tags and common-ci, which the versions are worked out from' {
        foreach ($testing in $script:Testing) {
            $checkouts = @(Get-Step $testing 'actions/checkout')
            $own = @($checkouts | Where-Object {
                    -not (Get-Value $_ 'repository') })
            $own.Count | Should -Be 1
            Get-Value $own[0] 'fetch-depth' | Should -Be '0'
            $commonCi = @($checkouts | Where-Object {
                    (Get-Value $_ 'repository') -eq '51Degrees/common-ci' })
            $commonCi.Count | Should -Be 1
            $path = Get-Value $commonCi[0] 'path'
            ($script:Jobs[$testing] -join "`n") |
                Should -Match "(?m)^\s+_51DEGREES_COMMON_CI_DIR:.*$([regex]::Escape($path))"
        }
    }

    It 'fails the install step when pip fails' {
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            $text | Should -Match ('- name: Install the packages the tests use' +
                '\s*\n(\s+\S.*\n)*?\s+\$PSNativeCommandUseErrorActionPreference = \$true')
        }
    }
}

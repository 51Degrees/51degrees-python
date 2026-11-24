# Tests that .github/workflows/free-threaded-python.yml fetches the free Lite
# data files once, in one job, and that the jobs that test take them from the
# cache that job fills, rather than each downloading them again.
# The workflow is read as text, as the runners have no YAML module.

BeforeAll {
    $script:Workflow = Join-Path $PSScriptRoot '..' '.github' 'workflows' `
        'free-threaded-python.yml'
    $lines = @(Get-Content -LiteralPath $script:Workflow)

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
                ($_ -join "`n") -match "uses:\s*$([regex]::Escape($Uses))@" })
    }

    # The lines of a "path: |" block in a step, trimmed.
    function Get-Paths($Step) {
        $paths = @()
        $inPaths = $false
        foreach ($line in $Step) {
            if ($line -match '^\s+path:\s*\|\s*$') { $inPaths = $true; continue }
            if ($inPaths -and $line -match '^\s{12,}\S') {
                $paths += $line.Trim()
                continue
            }
            $inPaths = $false
        }
        return $paths
    }

    function Get-Value($Step, [string]$Key) {
        foreach ($line in $Step) {
            if ($line -match "^\s+$Key\:\s*(.+?)\s*$") { return $Matches[1] }
        }
    }

    $script:Fetching = @($script:Jobs.Keys | Where-Object {
            ($script:Jobs[$_] -join "`n") -match 'get-data-files\.ps1' })
    $script:Testing = @($script:Jobs.Keys | Where-Object {
            ($script:Jobs[$_] -join "`n") -match 'pytest' })
}

Describe 'free-threaded-python.yml' {
    It 'downloads the free data files in one job only' {
        $script:Fetching.Count | Should -Be 1
    }

    It 'downloads them in a job that is not a matrix' {
        foreach ($job in $script:Fetching) {
            ($script:Jobs[$job] -join "`n") | Should -Not -Match 'matrix:'
        }
    }

    It 'never downloads them in a job that runs the tests' {
        $script:Testing.Count | Should -BeGreaterThan 0
        foreach ($job in $script:Testing) {
            $script:Fetching | Should -Not -Contain $job
        }
    }

    It 'saves them in the cache, and downloads them only when it misses' {
        $job = $script:Fetching[0]
        $cache = @(Get-Step $job 'actions/cache')
        $cache.Count | Should -Be 1
        Get-Value $cache[0] 'id' | Should -Not -BeNullOrEmpty
        $id = Get-Value $cache[0] 'id'
        $fetch = ($script:Jobs[$job] -join "`n")
        $fetch | Should -Match ("if:\s*steps\.$id\.outputs\.cache-hit\s*!=\s*" +
            "'true'\s*\n\s+run:\s*[|]?\s*\n?\s*\./cxx/data/get-data-files\.ps1")
    }

    It 'restores them in each job that runs the tests, from the same key and paths' {
        $job = $script:Fetching[0]
        $save = @(Get-Step $job 'actions/cache')[0]
        $keyStep = Get-Value $save 'key'
        $keyStep | Should -Match '^\$\{\{\s*steps\.([\w-]+)\.outputs\.key\s*\}\}$'
        ($script:Jobs[$job] -join "`n") | Should -Match (
            '\n    outputs:\s*\n\s+key:\s*' + [regex]::Escape($keyStep))
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            $text | Should -Match "\n    needs:\s*\[?\s*$([regex]::Escape($job))\b"
            $restore = @(Get-Step $testing 'actions/cache/restore')
            $restore.Count | Should -Be 1
            Get-Value $restore[0] 'key' |
                Should -Be ('${{ needs.' + $job + '.outputs.key }}')
            Get-Value $restore[0] 'fail-on-cache-miss' | Should -Be 'true'
            Get-Paths $restore[0] | Should -Be (Get-Paths $save)
        }
    }

    It 'saves and restores across operating systems, for the Windows jobs' {
        $job = $script:Fetching[0]
        $steps = @(Get-Step $job 'actions/cache') + @($script:Testing |
                ForEach-Object { Get-Step $_ 'actions/cache/restore' })
        $steps.Count | Should -BeGreaterThan 1
        foreach ($step in $steps) {
            Get-Value $step 'enableCrossOsArchive' | Should -Be 'true'
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

    It 'sets <Variable> to the restored <File> before the tests run' -ForEach @(
        @{ Variable = '_51DEGREES_DD_PATH'; File = '51Degrees-LiteV4.1.hash' }
        @{ Variable = '_51DEGREES_IPI_PATH'; File = '51Degrees-LiteV41.ipi' }
    ) {
        $paths = Get-Paths (@(Get-Step $script:Fetching[0] 'actions/cache')[0])
        $paths | Should -Contain "cxx/data/**/$File"
        foreach ($testing in $script:Testing) {
            $text = $script:Jobs[$testing] -join "`n"
            $set = [regex]::Match($text, ('(?m)^\s+\$env:' + $Variable +
                    '\s*=\s*\(Resolve-Path cxx/data/[\w-]+/' +
                    [regex]::Escape($File) + '\)\.Path\s*$'))
            $set.Success | Should -BeTrue
            $set.Index | Should -BeLessThan $text.IndexOf('python -m pytest')
        }
    }

    It 'caches each of the free data files the tests use' {
        $paths = Get-Paths (@(Get-Step $script:Fetching[0] 'actions/cache')[0])
        foreach ($file in '51Degrees-LiteV4.1.hash', '51Degrees-LiteV41.ipi',
            '51Degrees-IPIV4AsnIpiV41.ipi', '20000 Evidence Records.yml') {
            $paths | Should -Contain "cxx/data/**/$file"
        }
        # The evidence is the YAML file, and no other evidence file is cached.
        @($paths | Where-Object { $_ -notmatch '\.(hash|ipi|yml)$' }) |
            Should -BeNullOrEmpty
    }
}

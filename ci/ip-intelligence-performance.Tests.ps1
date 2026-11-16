# Tests for ip-intelligence/ci/run-performance-tests.ps1.
#
# common-ci runs the script from its own folder, which holds the assets, with
# the product folder as RepoName. Each test lays out such a folder with empty
# stand-ins for the free Lite data file and the evidence, and mocks python, so
# that what is checked is what the script measures and on which file, not the
# measurement itself.

BeforeAll {
    $script:Script = Join-Path $PSScriptRoot '..' 'ip-intelligence' 'ci' `
        'run-performance-tests.ps1'

    # The free data file and the evidence, as common-ci's assets name them.
    $script:LiteFile = '51Degrees-LiteIpiV41.ipi'
    $script:EvidenceFile = 'ip-intelligence-evidence.yml'

    # The web benchmark, in the same place as Device Detection's, and the
    # console example, relative to the product folder.
    $script:WebBenchmark =
        'fiftyone_ipintelligence_examples/performance-tests/test_performance.py'
    $script:ConsoleBenchmark = 'fiftyone_ipintelligence_examples/src/' +
        'fiftyone_ipintelligence_examples/onpremise/performance_console.py'

    # The name of the file that follows $Option in the arguments, or null.
    function Get-OptionFile([object[]]$Arguments, [string]$Option) {
        $index = [Array]::IndexOf($Arguments, $Option)
        if ($index -lt 0) {
            return $null
        }
        return Split-Path -Leaf $Arguments[$index + 1]
    }
}

Describe 'ip-intelligence run-performance-tests.ps1' {

BeforeEach {
    $script:CommonCi = Join-Path ([IO.Path]::GetTempPath()) `
        ([Guid]::NewGuid().ToString())
    $script:Assets = New-Item -ItemType Directory -Force `
        (Join-Path $script:CommonCi 'assets')
    $script:Product = (New-Item -ItemType Directory -Force `
        (Join-Path $script:CommonCi 'ip-intelligence')).FullName
    foreach ($name in $script:LiteFile, $script:EvidenceFile) {
        Set-Content (Join-Path $script:Assets $name) ''
    }

    # The console benchmark writes its summary where --json_output says.
    Mock python {
        $index = [Array]::IndexOf($args, '--json_output')
        if ($index -ge 0) {
            '{ "DetectionsPerSecond": 1, "MsPerDetection": 1 }' |
                Set-Content $args[$index + 1]
        }
    }

    Push-Location $script:CommonCi
}

AfterEach {
    Pop-Location
    Remove-Item -Recurse -Force $script:CommonCi
}

It 'has a web benchmark in the same form as Device Detection' {
    Join-Path $PSScriptRoot '..' 'ip-intelligence' $script:WebBenchmark |
        Should -Exist
}

It 'runs the web benchmark on the free Lite file and the evidence' {
    & $script:Script -RepoName $script:Product -Name 'test' | Out-Null

    Should -Invoke python -Times 1 -Exactly -ParameterFilter {
        $args[0] -eq $script:WebBenchmark -and
        (Split-Path -Leaf $args[1]) -eq $script:LiteFile -and
        (Split-Path -Leaf $args[2]) -eq $script:EvidenceFile -and
        $args -contains '--output'
    }
}

It 'runs the console benchmark on the free Lite file and the evidence' {
    $output = & $script:Script -RepoName $script:Product -Name 'test' |
        Out-String

    Should -Invoke python -Times 1 -Exactly -ParameterFilter {
        $args[0] -eq $script:ConsoleBenchmark -and
        (Get-OptionFile $args '--data_file') -eq $script:LiteFile -and
        (Get-OptionFile $args '--evidence_file') -eq $script:EvidenceFile
    }
    $output | Should -Match 'on 51Degrees-LiteIpiV41\.ipi'
}

It 'writes the summary the performance step reports' {
    & $script:Script -RepoName $script:Product -Name 'test' | Out-Null

    $summary = Join-Path $script:Product 'test-results' 'performance-summary' `
        'results_test.json'
    $summary | Should -Exist
    $results = Get-Content $summary | ConvertFrom-Json
    $results.HigherIsBetter.DetectionsPerSecond | Should -Be 1
    $results.LowerIsBetter.AvgMillisecsPerDetection | Should -Be 1
}

It 'fails rather than skipping when the free Lite file is absent' {
    Remove-Item (Join-Path $script:Assets $script:LiteFile)

    { & $script:Script -RepoName $script:Product -Name 'test' } |
        Should -Throw "*$($script:LiteFile)*"
    Should -Invoke python -Times 0 -Exactly
}

It 'runs nothing when performance is turned off' {
    & $script:Script -RepoName $script:Product -Name 'test' `
        -RunPerformance $false

    Should -Invoke python -Times 0 -Exactly
}

}

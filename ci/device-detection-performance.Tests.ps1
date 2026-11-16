# Tests for device-detection/ci/run-performance-tests.ps1.
#
# common-ci runs the script from its own folder, which holds the assets, with
# the product folder as RepoName. Each test lays out such a folder with empty
# stand-ins for the data files, and mocks python, so that what is checked is
# which data file the script measures on, not the measurement itself.

BeforeAll {
    $script:Script = Join-Path $PSScriptRoot '..' 'device-detection' 'ci' `
        'run-performance-tests.ps1'

    # The name of the file given to the console benchmark as --data_file.
    function Get-DataFileArgument([object[]]$Arguments) {
        $index = [Array]::IndexOf($Arguments, '--data_file')
        if ($index -lt 0) {
            return $null
        }
        return Split-Path -Leaf $Arguments[$index + 1]
    }
}

Describe 'device-detection run-performance-tests.ps1' {

BeforeEach {
    $script:CommonCi = Join-Path ([IO.Path]::GetTempPath()) `
        ([Guid]::NewGuid().ToString())
    $script:Assets = New-Item -ItemType Directory -Force `
        (Join-Path $script:CommonCi 'assets')
    $script:Product = (New-Item -ItemType Directory -Force `
        (Join-Path $script:CommonCi 'device-detection')).FullName
    foreach ($name in '51Degrees-LiteV4.1.hash', '20000 User Agents.csv') {
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

It 'measures on the free Lite file when the TAC file is absent' {
    $output = & $script:Script -RepoName $script:Product -Name 'test' |
        Out-String

    Should -Invoke python -Times 1 -Exactly -ParameterFilter {
        (Get-DataFileArgument $args) -eq '51Degrees-LiteV4.1.hash'
    }
    $output | Should -Match 'on 51Degrees-LiteV4\.1\.hash'
    Join-Path $script:Product 'test-results' 'performance-summary' `
        'results_test.json' | Should -Exist
}

It 'measures on the TAC file when it is there' {
    Set-Content (Join-Path $script:Assets 'TAC-HashV41.hash') ''

    $output = & $script:Script -RepoName $script:Product -Name 'test' |
        Out-String

    Should -Invoke python -Times 1 -Exactly -ParameterFilter {
        (Get-DataFileArgument $args) -eq 'TAC-HashV41.hash'
    }
    $output | Should -Match 'on TAC-HashV41\.hash'
}

It 'runs nothing when performance is turned off' {
    & $script:Script -RepoName $script:Product -Name 'test' `
        -RunPerformance $false

    Should -Invoke python -Times 0 -Exactly
}

}

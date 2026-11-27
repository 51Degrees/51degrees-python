# Tests for ci/select-options.ps1, with the entries of the real options.json
# read as common-ci's steps/select-options.ps1 reads them, as hashtables.

BeforeAll {
    $script:Select = Join-Path $PSScriptRoot 'select-options.ps1'

    # The names of the entries chosen for the changed files given, and the
    # entries themselves in $script:Chosen.
    function Get-Chosen([string[]]$ChangedFiles, [string[]]$CommentOnlyFiles = @()) {
        $options = @(Get-Content -Raw (Join-Path $PSScriptRoot 'options.json') |
            ConvertFrom-Json -AsHashtable)
        $script:Chosen = @(& $script:Select -Options $options `
            -ChangedFiles $ChangedFiles -CommentOnlyFiles $CommentOnlyFiles 6>$null)
        return @($script:Chosen | ForEach-Object { $_.Name } | Sort-Object)
    }

    $script:StandardSet = @('Ubuntu_Python_3.10', 'Ubuntu_Python_3.14')
}

Describe 'select-options.ps1' {
    It 'builds the standard set for a change to a package''s code' {
        Get-Chosen @('pipeline/fiftyone_pipeline_core/src/fiftyone_pipeline_core/flowdata.py') |
            Should -Be $script:StandardSet
    }

    It 'runs the Selenium contract on Python 3.14 alone, and no performance tests' {
        $null = Get-Chosen @('location/src/fiftyone_location/location_cloud.py')
        foreach ($entry in $script:Chosen) {
            $entry.SeleniumContract | Should -Be ($entry.Name -eq 'Ubuntu_Python_3.14')
            $entry.RunPerformance | Should -BeFalse
        }
    }

    It 'adds Windows for a change to an on-premise package' {
        Get-Chosen @('device-detection/fiftyone_devicedetection_onpremise/src/fiftyone_devicedetection_onpremise/swig_data.py') |
            Should -Be (@($script:StandardSet + 'Windows_Python_3.14') | Sort-Object)
    }

    It 'adds Windows for a change to the cxx submodule' {
        Get-Chosen @('cxx') |
            Should -Be (@($script:StandardSet + 'Windows_Python_3.14') | Sort-Object)
    }

    It 'leaves Windows out for a change only to the comments of an on-premise file' {
        $file = 'ip-intelligence/fiftyone_ipintelligence_onpremise/src/fiftyone_ipintelligence_onpremise/swig_data.py'
        Get-Chosen @($file) @($file) | Should -Be $script:StandardSet
    }

    It 'adds Python 3.11 to 3.13 on Linux for a change to a setup.py' {
        Get-Chosen @('location/setup.py') | Should -Be (@($script:StandardSet +
            'Ubuntu_Python_3.11' + 'Ubuntu_Python_3.12' + 'Ubuntu_Python_3.13') |
            Sort-Object)
    }

    It 'builds every entry but macOS for a change to <Case>' -ForEach @(
        @{ Case = 'a ci folder'; File = 'device-detection/ci/build-project.ps1' }
        @{ Case = 'the root ci folder'; File = 'ci/packages.ps1' }
        @{ Case = 'a file outside the product folders'; File = '.github/workflows/pull-requests.yml' }
    ) {
        $chosen = Get-Chosen @($File)
        $chosen.Count | Should -Be 10
        $chosen | Where-Object { $_ -like 'macOS*' } | Should -BeNullOrEmpty
    }

    It 'never builds macOS on a pull request' {
        Get-Chosen @('cxx', 'ci/packages.ps1', 'location/setup.py') |
            Where-Object { $_ -like 'macOS*' } | Should -BeNullOrEmpty
    }
}

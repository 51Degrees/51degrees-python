# The TAC data file and the property CSV come from the Distributor with the data
# license, which common-ci's steps/fetch-assets.ps1 reads from
# _51DEGREES_LICENSE_KEY. No key is passed to it.
$ErrorActionPreference = 'Stop'

# PreBuild is a job from the nightly-publish-main workflow
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping assets fetching"
    exit 0
}

$data = "$PSScriptRoot/../../cxx/data"
$deviceDetectionData = "$data/device-detection"

$assets = '51Degrees-LiteV4.1.hash', '20000 Evidence Records.yml',
    'TAC-HashV41.hash', '51Degrees.csv'

./steps/fetch-assets.ps1 -Assets $assets
foreach ($asset in $assets) {
    switch -Exact -CaseSensitive ($asset) {
        'TAC-HashV41.hash' {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$deviceDetectionData/Enterprise-HashV41.hash"}
        '51Degrees.csv' {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$PSScriptRoot/../fiftyone_devicedetection_cloud/tests/$_"}
        '51Degrees-LiteV4.1.hash' {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$deviceDetectionData/$_", "$PSScriptRoot/../fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/onpremise/gettingstarted_web/$_"}
        default {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$deviceDetectionData/$_"}
    }
}

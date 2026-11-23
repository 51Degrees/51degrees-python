param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [boolean]$RunPerformance = $True
)

if (!$RunPerformance) {
    Write-Output "Skipping performance tests"
    return
}

# Every example and test runs on the free data files, so without the licensed
# TAC file the console benchmark measures on the Lite file rather than not at
# all. fetch-assets.ps1 always fetches the Lite file, so its absence is an
# error, not a reason to skip.
$dataFileName = 'TAC-HashV41.hash'
if (!(Test-Path "assets/$dataFileName")) {
    $dataFileName = '51Degrees-LiteV4.1.hash'
    if (!(Test-Path "assets/$dataFileName")) {
        throw "Neither TAC-HashV41.hash nor $dataFileName is in the assets, so the performance tests cannot run"
    }
}

$perfSummary = New-Item -ItemType directory -Path $RepoName/test-results/performance-summary -Force

# The assets are in the common-ci folder this runs from. The tests below run
# from the product's folder, so the path is resolved first: '../assets' from
# there only worked while the product was a repository of its own.
$assets = (Resolve-Path assets).Path

Push-Location $RepoName
try {
    Write-Output "Running Web performance tests"
    python fiftyone_devicedetection_examples/performance-tests/test_performance.py "$assets/51Degrees-LiteV4.1.hash" "$assets/20000 Evidence Records.yml" --output || $(throw "benchmark failed with code: $LASTEXITCODE")

    Write-Output "Running Console performance tests on $dataFileName"
    python fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/onpremise/performance.py --data_file "$assets/$dataFileName" --evidence_file "$assets/20000 Evidence Records.yml" --json_output $pwd/summary.json || $(throw "performance tests failed with $LASTEXITCODE")

    $Results = Get-Content $pwd/summary.json | ConvertFrom-Json
    @{
        HigherIsBetter = @{
            DetectionsPerSecond = $Results.DetectionsPerSecond
        };
        LowerIsBetter = @{
            AvgMillisecsPerDetection = $Results.MsPerDetection
        }
    } | ConvertTo-Json | Out-File $perfSummary/results_$Name.json
} finally {
    Pop-Location
}

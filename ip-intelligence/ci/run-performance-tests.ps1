param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [boolean]$RunPerformance = $True
)
$ErrorActionPreference = 'Stop'

if (!$RunPerformance) {
    Write-Output "Skipping performance tests"
    return
}

# Every example and test runs on the free data files, so the benchmarks
# measure on the free Lite file, which needs no licence. fetch-assets.ps1
# always fetches it and the evidence, so either one missing is an error, not
# a reason to skip. The Lite file is used rather than the smaller Asn file
# because it has RegisteredCountry, the property the benchmarks read, so each
# lookup returns a value as it does with a paid file.
$dataFileName = '51Degrees-LiteIpiV41.ipi'
$evidenceFileName = 'ip-intelligence-evidence.yml'
foreach ($name in $dataFileName, $evidenceFileName) {
    if (!(Test-Path "assets/$name")) {
        throw "$name is not in the assets, so the performance tests cannot run"
    }
}

$perfSummary = New-Item -ItemType directory -Path $RepoName/test-results/performance-summary -Force

# The assets are in the common-ci folder this runs from. The tests below run
# from the product's folder, so the path is resolved first.
$assets = (Resolve-Path assets).Path

Push-Location $RepoName
try {
    Write-Output "Running Web performance tests on $dataFileName"
    python fiftyone_ipintelligence_examples/performance-tests/test_performance.py "$assets/$dataFileName" "$assets/$evidenceFileName" --output || $(throw "benchmark failed with code: $LASTEXITCODE")

    Write-Output "Running Console performance tests on $dataFileName"
    python fiftyone_ipintelligence_examples/src/fiftyone_ipintelligence_examples/onpremise/performance_console.py --data_file "$assets/$dataFileName" --evidence_file "$assets/$evidenceFileName" --json_output $pwd/summary.json || $(throw "performance tests failed with $LASTEXITCODE")

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

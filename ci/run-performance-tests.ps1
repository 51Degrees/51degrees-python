param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [boolean]$RunPerformance = $True
)

# Performance tests are not yet implemented for ip-intelligence-python.
# They should mirror the approach used by device-detection-python's
# performance-tests once a stable data file source is available in CI.
Write-Output "Skipping performance tests - not yet implemented for ip-intelligence-python"

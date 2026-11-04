param (
    [string]$IpIntelligence,
    [string]$IpIntelligenceUrl
)
$ErrorActionPreference = 'Stop'

# PreBuild is a job from the nightly-publish-main workflow
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping assets fetching"
    exit 0
}

$assetsDir = "$PSScriptRoot/../assets"
New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

$assets = '51Degrees-LiteIpiV41.ipi', 'ip-intelligence-evidence.yml'
if ($IpIntelligenceUrl) {
    $assets += '51Degrees-EnterpriseIpiV41.ipi'
} else {
    Write-Host "::warning file=$($MyInvocation.ScriptName),line=$($MyInvocation.ScriptLineNumber),title=No Data File Url::An IP intelligence data file URL was not provided, so the Enterprise data file will not be downloaded."
}

./steps/fetch-assets.ps1 -IpIntelligence:$IpIntelligence -IpIntelligenceUrl:$IpIntelligenceUrl -Assets $assets

foreach ($asset in $assets) {
    switch -Exact -CaseSensitive ($asset) {
        'ip-intelligence-evidence.yml' {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$assetsDir/evidence.yml"}
        default {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$assetsDir/$_"}
    }
}

# The ASN file is not an asset, so the data repository's script downloads it
# beside its link in cxx/data/ip-intelligence, where the tests look for it.
$global:LASTEXITCODE = 0
& "$PSScriptRoot/../../cxx/data/get-data-files.ps1" 51Degrees-IPIV4AsnIpiV41.ipi
if ($LASTEXITCODE -ne 0) {
    throw "The ASN data file was not downloaded"
}

# If the Enterprise file was downloaded, prefer it for tests by exposing
# it through the environment variable used by the test suites.
if ($IpIntelligenceUrl) {
    Write-Output "IPINTELLIGENCEDATAFILE=$assetsDir/51Degrees-EnterpriseIpiV41.ipi" | Out-File -Append -FilePath $env:GITHUB_ENV -ErrorAction SilentlyContinue
}

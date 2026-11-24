# The Enterprise data file comes from the Distributor with the data license,
# which common-ci's steps/fetch-assets.ps1 reads from _51DEGREES_LICENSE_KEY.
# No key or address is passed to it.
$ErrorActionPreference = 'Stop'

# PreBuild is a job from the nightly-publish-main workflow
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping assets fetching"
    exit 0
}

$assetsDir = "$PSScriptRoot/../assets"
New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

# The mixed examples use the device detection Lite data file as well, so it
# is fetched here too, for a run that tests IP Intelligence alone.
$assets = '51Degrees-LiteIpiV41.ipi', 'ip-intelligence-evidence.yml',
    '51Degrees-EnterpriseIpiV41.ipi', '51Degrees-LiteV4.1.hash'

./steps/fetch-assets.ps1 -Assets $assets

foreach ($asset in $assets) {
    switch -Exact -CaseSensitive ($asset) {
        'ip-intelligence-evidence.yml' {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$assetsDir/evidence.yml"}
        default {New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/$_" -Path "$assetsDir/$_"}
    }
}

# The tests look for the Asn file in cxx/data/ip-intelligence, and the examples
# look there for the Lite data file, under the name the data repository saves
# it as. Both are assets, so a test job restores them from the run's cache
# rather than downloading them.
$ipIntelligenceData = "$PSScriptRoot/../../cxx/data/ip-intelligence"
New-Item -ItemType SymbolicLink -Force -Target "$PWD/assets/51Degrees-LiteIpiV41.ipi" -Path "$ipIntelligenceData/51Degrees-LiteV41.ipi"
$asn = '51Degrees-IPIV4AsnIpiV41.ipi'
./steps/fetch-assets.ps1 -Assets $asn
Copy-Item "assets/$asn" $ipIntelligenceData

# The tests and examples find their data file through the environment
# variable the test suites read. They accept the Lite file, so it is the one
# named. common-ci runs the tests in the same process as this script, so the
# variable is set in this process.
$env:_51DEGREES_IPI_PATH = (Resolve-Path "assets/51Degrees-LiteIpiV41.ipi").Path
$env:_51DEGREES_DD_PATH = (Resolve-Path "assets/51Degrees-LiteV4.1.hash").Path

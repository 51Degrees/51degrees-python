param(
    # Every entry of options.json.
    [Parameter(Mandatory)][object[]]$Options,
    # The files the pull request changes, less documentation.
    [string[]]$ChangedFiles,
    # Those of the changed files whose change touches only comments.
    [string[]]$CommentOnlyFiles
)
# Chooses the options.json entries a pull request is built on, for common-ci's
# steps/select-options.ps1. The branch itself and a release build every entry.
# Within each entry, packages.ps1 still builds only the products the change
# touches.
#
# The standard set is Python 3.14 and 3.10 on Linux, the newest and the oldest,
# with the Selenium contract on 3.14 alone. A change in more than its comments
# to an on-premise package, its data or the cxx submodule adds Windows, where
# the native module is built differently. A change to a setup.py, setup.cfg or
# pyproject.toml adds Python 3.11 to 3.13 on Linux, and a change outside the
# product folders or to a ci folder adds every entry. Only five macOS jobs run
# at once across the organisation, and the releases need them, so macOS is left
# to the branch and release builds, as is performance.

$Standard = @('Ubuntu_Python_3.14', 'Ubuntu_Python_3.10')
$Contract = 'Ubuntu_Python_3.14'
$Native = @('Windows_Python_3.14')
$Versions = @('Ubuntu_Python_3.13', 'Ubuntu_Python_3.12', 'Ubuntu_Python_3.11')
$ProductFolders = @('pipeline/', 'device-detection/', 'ip-intelligence/',
    'location/')
$NativePaths = @('device-detection/fiftyone_devicedetection_onpremise/',
    'ip-intelligence/fiftyone_ipintelligence_onpremise/',
    'ip-intelligence/ip-intelligence-data')

function Test-Under([string]$Path, [string[]]$Prefixes) {
    return @($Prefixes | Where-Object {
        $Path -eq $_.TrimEnd('/') -or $Path.StartsWith($_.TrimEnd('/') + '/')
    }).Count -gt 0
}

$code = @($ChangedFiles | Where-Object { $CommentOnlyFiles -notcontains $_ })
$native = @($code | Where-Object {
    $_ -eq 'cxx' -or (Test-Under $_ $NativePaths)
}).Count -gt 0
$setup = @($code | Where-Object {
    $_ -match '(^|/)(setup\.py|setup\.cfg|pyproject\.toml)$'
}).Count -gt 0
$other = @($code | Where-Object {
    $_ -ne 'cxx' -and (!(Test-Under $_ $ProductFolders) -or $_ -match '(^|/)ci/')
}).Count -gt 0
Write-Host ("Native: $native. Setup: $setup. " +
    "Outside the product folders or in a ci folder: $other.")

foreach ($entry in $Options) {
    $name = $entry.Name
    if ($entry.Image -like 'macos*') {
        Write-Host "$name is left to the branch and release builds"
        continue
    }
    $why = if ($Standard -contains $name) { 'the standard set' }
        elseif ($other) { 'a change outside the product folders or to CI' }
        elseif ($native -and $Native -contains $name) { 'a native change' }
        elseif ($setup -and $Versions -contains $name) { 'a packaging change' }
    if (!$why) {
        Write-Host "$name is not needed for this change"
        continue
    }
    $entry.SeleniumContract = $name -eq $Contract
    $entry.RunPerformance = $false
    Write-Host "$name runs for $why"
    $entry
}

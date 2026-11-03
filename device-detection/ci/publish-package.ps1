param (
    [Parameter(Mandatory=$true)]
    [Hashtable]$Keys,
    [bool]$DryRun = $False
)

./python/publish-package-pypi.ps1 -Keys $Keys -DryRun $DryRun

exit $LASTEXITCODE

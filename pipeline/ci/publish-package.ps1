param (
    [bool]$DryRun = $False
)

./python/publish-package-pypi.ps1 -DryRun $DryRun

exit $LASTEXITCODE

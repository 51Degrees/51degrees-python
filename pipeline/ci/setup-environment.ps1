param (
    [Parameter(Mandatory=$true)]
    [string]$LanguageVersion
)

# PreBuild is a job from the nightly-publish-main workflow
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping environment setup"
    exit 0
}

$dependencies = "tox", "pylint", "unittest-xml-reporting", "coverage", "parameterized", "requests-mock", "flask"
./python/setup-environment.ps1 -LanguageVersion $LanguageVersion -Dependencies $dependencies

exit $LASTEXITCODE

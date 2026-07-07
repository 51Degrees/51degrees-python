param (
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [string]$LanguageVersion
)

# PreBuild is a job from the nightly-publish-main workflow
if ($env:GITHUB_JOB -eq "PreBuild") {
    Write-Output "Skipping environment setup"
    exit 0
}

$dependencies = "-r", "$RepoName/requirements.txt", "wheel", `
                "tox", "pylint", "unittest-xml-reporting", "coverage", "certifi", `
                "requests", "cachetools", "chevron", "jsmin", "ruamel.yaml", `
                "fiftyone_pipeline_cloudrequestengine", `
                "fiftyone_pipeline_core", `
                "fiftyone_pipeline_engines", `
                "fiftyone_pipeline_engines_fiftyone"

./python/setup-environment.ps1 -LanguageVersion $LanguageVersion -Dependencies $dependencies

exit $LASTEXITCODE

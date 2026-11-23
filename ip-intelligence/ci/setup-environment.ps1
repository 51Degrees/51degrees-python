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

# setuptools is listed because common-ci's build-project.ps1 builds the
# on-premise extension in place with 'python setup.py', and Python 3.12 and
# later no longer install setuptools with the interpreter. Without it that
# build failed with "No module named 'setuptools'", the failure was not
# checked, and pylint later failed instead for want of the extension.
$dependencies = "-r", "$RepoName/requirements.txt", "wheel", "setuptools", `
                "tox", "pylint", "unittest-xml-reporting", "coverage", "certifi", `
                "requests", "cachetools", "chevron", "jsmin", "ruamel.yaml", `
                "fiftyone_pipeline_cloudrequestengine", `
                "fiftyone_pipeline_core", `
                "fiftyone_pipeline_engines", `
                "fiftyone_pipeline_engines_fiftyone"

./python/setup-environment.ps1 -LanguageVersion $LanguageVersion -Dependencies $dependencies

exit $LASTEXITCODE

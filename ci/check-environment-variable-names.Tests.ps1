# Tests for ci/check-environment-variable-names.ps1.
#
# Each case is one line of text and what the check must make of it. Names are
# matched in any case, because Windows reads an environment variable name in
# any case, so a lower case old name is still the old name there.

BeforeAll {
    . (Join-Path $PSScriptRoot 'check-environment-variable-names.ps1')

    function Get-Kind([string]$Line) {
        @(Find-EnvironmentNameProblem $Line | ForEach-Object { $_.Kind })
    }
}

Describe 'Find-EnvironmentNameProblem' {

    It 'finds the digit-initial name <Line>' -ForEach @(
        @{ Line = '$env:51DEGREES_DD_PATH = "file.hash"' }
        @{ Line = 'export 51DEGREES_IPI_PATH=file.ipi' }
        @{ Line = 'os.environ.get("51degrees_dd_path")' }
        @{ Line = '$env:51Degrees_Resource_Key = "key"' }
    ) {
        Get-Kind $Line | Should -Contain 'digit'
    }

    It 'finds the fallback name <Line>' -ForEach @(
        @{ Line = 'os.environ.get("RESOURCE_KEY")' }
        @{ Line = 'os.environ.get("resource_key")' }
        @{ Line = 'os.environ["license_key"]' }
        @{ Line = 'os.getenv(''License_Key'')' }
        @{ Line = 'if "resource_key" in os.environ:' }
        @{ Line = '$env:resource_key = "key"' }
        @{ Line = '[Environment]::SetEnvironmentVariable("license_key", $k)' }
        @{ Line = 'RESOURCE = env("_51DEGREES_RESOURCE_KEY", "RESOURCE_KEY")' }
        @{ Line = 'LICENCE = env("_51DEGREES_LICENSE_KEY", "license_key")' }
        @{ Line = 'LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"' }
        @{ Line = 'legacy_license_key_env_var = "x"' }
        @{ Line = 'self.baseURL = os.environ.get("FOD_CLOUD_API_URL")' }
        @{ Line = 'FOD_CLOUD_API_URL = "FOD_CLOUD_API_URL"' }
        @{ Line = 'ENDPOINT_ENV_VAR = "cloud_endpoint"' }
        @{ Line = 'ORIGIN_ENV_VAR = "cloud_request_origin"' }
        @{ Line = '$env:cloud_endpoint = "https://cloud.51degrees.com/api/v4/"' }
        @{ Line = 'env = os.environ.get("IPINTELLIGENCEDATAFILE")' }
        @{ Line = 'os.environ["ipintelligencetestkey"] = "value"' }
        @{ Line = 'if "run_performance_tests" in os.environ:' }
        @{ Line = 'saved = os.environ.pop("FOD_CLOUD_API_URL", None)' }
    ) {
        Get-Kind $Line | Should -Contain 'fallback'
    }

    # cloud_endpoint is a pipeline setting as well as an old variable name,
    # and only the variable moves, so a setting written by its key is left
    # alone.
    It 'leaves <Line> alone' -ForEach @(
        @{ Line = 'os.environ.get("_51DEGREES_RESOURCE_KEY")' }
        @{ Line = 'pipeline_settings["cloud_endpoint"] = cloud_endpoint' }
        @{ Line = 'cloudRequestEngineSettings["cloud_endpoint"] = cloudEndPoint' }
        @{ Line = 'def run(self, resource_key, logger, cloud_endpoint = None):' }
        @{ Line = 'ENDPOINT_VARIABLE = "_51DEGREES_CLOUD_ENDPOINT"' }
        @{ Line = '$env:_51DEGREES_DD_PATH = "file.hash"' }
        @{ Line = '$env:_51DEGREES_LICENSE_KEY_51DID = $k' }
        @{ Line = 'RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"' }
        @{ Line = 'builder = Builder({"resource_key": "YOUR_RESOURCE_KEY"})' }
        @{ Line = 'Builder(resource_key=key, license_key=licence)' }
        @{ Line = '$env:PAID_RESOURCE_KEY = $Keys.TestResourceKey' }
        @{ Line = 'Set the 51D_ cookie for the 51Did example.' }
    ) {
        Get-Kind $Line | Should -BeNullOrEmpty
    }
}

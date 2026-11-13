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
        @{ Line = 'LEGACY_RESOURCE_KEY_ENV_VAR = "resource_key"' }
        @{ Line = 'self.baseURL = os.environ.get("FOD_CLOUD_API_URL")' }
        @{ Line = 'FOD_CLOUD_API_URL = "FOD_CLOUD_API_URL"' }
        @{ Line = 'saved = os.environ.pop("FOD_CLOUD_API_URL", None)' }
        @{ Line = '$env:FOD_CLOUD_API_URL = "https://cloud.51degrees.com/api/v4/"' }
        @{ Line = 'key = env("_51DEGREES_RESOURCE_KEY", "resource_key") or os.environ.get("license_key")' }
        @{ Line = 'RESOURCE_KEY_ENV_VAR = "resource_key"' }
        @{ Line = 'ENDPOINT_ENV_VAR = "cloud_endpoint"' }
        @{ Line = 'ORIGIN_ENV_VAR = "cloud_request_origin"' }
        @{ Line = 'os.environ.get("cloud_request_origin")' }
        @{ Line = '$env:cloud_endpoint = "https://cloud.51degrees.com/api/v4/"' }
        @{ Line = '${env:cloud_endpoint} = "https://cloud.51degrees.com/api/v4/"' }
        @{ Line = '${Env:RESOURCE_KEY}' }
        @{ Line = 'Remove-Item Env:\license_key' }
        @{ Line = '          url: ${{ env.cloud_endpoint }}' }
        @{ Line = 'env = os.environ.get("IPINTELLIGENCEDATAFILE")' }
        @{ Line = 'os.environ["ipintelligencetestkey"] = "value"' }
        @{ Line = 'if "run_performance_tests" in os.environ:' }
    ) {
        Get-Kind $Line | Should -Contain 'fallback'
    }

    # cloud_endpoint is a pipeline setting as well as an old variable name,
    # and only the variable moves, so a setting written by its key is left
    # alone.
    It 'leaves <Line> alone' -ForEach @(
        @{ Line = 'os.environ.get("_51DEGREES_RESOURCE_KEY")' }
        @{ Line = 'pipeline_settings["cloud_endpoint"] = cloud_endpoint' }
        @{ Line = 'resourceKey = "resource_key"' }
        @{ Line = 'class IpIntelligenceDataFile(DataFile):' }
        @{ Line = 'if isinstance(datafile, IpIntelligenceDataFile):' }
        @{ Line = 'RESOURCE_KEY = "resource_key"' }
        @{ Line = 'testResourceKey = "resource_key"' }
        @{ Line = 'def __init__(self, resource_key, cloud_request_origin=None):' }
        @{ Line = '"cloud_request_origin": cloud_request_origin,' }
        @{ Line = 'cloudRequestEngineSettings["cloud_endpoint"] = cloudEndPoint' }
        @{ Line = 'def run(self, resource_key, logger, cloud_endpoint = None):' }
        @{ Line = 'ENDPOINT_VARIABLE = "_51DEGREES_CLOUD_ENDPOINT"' }
        @{ Line = '$env:_51DEGREES_DD_PATH = "file.hash"' }
        @{ Line = '$env:_51DEGREES_LICENSE_KEY_51DID = $k' }
        @{ Line = 'RESOURCE_KEY_ENV_VAR = "_51DEGREES_RESOURCE_KEY"' }
        @{ Line = 'builder = Builder({"resource_key": "YOUR_RESOURCE_KEY"})' }
        @{ Line = 'Builder(resource_key=key, license_key=licence)' }
        @{ Line = '$env:PAID_RESOURCE_KEY = $Keys.TestResourceKey' }
        @{ Line = '${env:_51DEGREES_RESOURCE_KEY} = $Keys.TestResourceKey' }
        @{ Line = '  PAID_RESOURCE_KEY: ${{ env.PAID_RESOURCE_KEY }}' }
        @{ Line = 'Set the 51D_ cookie for the 51Did example.' }
    ) {
        Get-Kind $Line | Should -BeNullOrEmpty
    }

    # A variable whose name changed is still read under its old name when
    # the new one is not set. That read gives the old name as the argument
    # straight after the new one, and it is left alone.
    It 'leaves the deprecated read <Line> alone' -ForEach @(
        @{ Line = 'RESOURCE = env("_51DEGREES_RESOURCE_KEY", "RESOURCE_KEY")' }
        @{ Line = 'LICENCE = env("_51DEGREES_LICENSE_KEY", "license_key")' }
        @{ Line = 'API = env("_51DEGREES_CLOUD_ENDPOINT", "FOD_CLOUD_API_URL")' }
        @{ Line = 'read_environment("_51DEGREES_IPI_PATH", "IPINTELLIGENCEDATAFILE")' }
        @{ Line = '    "_51DEGREES_RUN_PERFORMANCE_TESTS", "run_performance_tests")' }
        @{ Line = "read_environment('_51DEGREES_DD_PATH', '51DEGREES_DD_PATH')" }
    ) {
        Get-Kind $Line | Should -BeNullOrEmpty
    }
}

Describe 'Find-EnvironmentNameProblem with the old names a file may hold' {

    It 'leaves <Line> alone when the file may hold <Allowed>' -ForEach @(
        @{ Line = 'ENDPOINT_ENV_VAR = "cloud_endpoint"'; Allowed = @('cloud_endpoint') }
        @{ Line = 'os.environ["resource_key"] = "old-key"'; Allowed = @('resource_key', 'license_key') }
        @{ Line = 'DATA_FILE_ENV_VAR = "51DEGREES_DD_PATH"'; Allowed = @('51DEGREES_DD_PATH') }
        @{ Line = '    FOD_CLOUD_API_URL'; Allowed = @('FOD_CLOUD_API_URL') }
        @{ Line = 'os.environ["RESOURCE_KEY"] = "old-resource-key"'; Allowed = @('RESOURCE_KEY') }
    ) {
        @(Find-EnvironmentNameProblem $Line $Allowed) | Should -BeNullOrEmpty
    }

    It 'finds <Kind> in <Line> when the file may hold only <Allowed>' -ForEach @(
        @{ Line = 'ENDPOINT_ENV_VAR = "cloud_endpoint"'; Allowed = @('resource_key'); Kind = 'fallback' }
        @{ Line = 'os.environ["license_key"] = "old-key"'; Allowed = @('resource_key'); Kind = 'fallback' }
        @{ Line = 'os.environ["RESOURCE_KEY"] = "old-key"'; Allowed = @('resource_key'); Kind = 'fallback' }
        @{ Line = '    IPINTELLIGENCEDATAFILE'; Allowed = @('FOD_CLOUD_API_URL'); Kind = 'fallback' }
        @{ Line = 'DATA_FILE_ENV_VAR = "51DEGREES_IPI_PATH"'; Allowed = @('51DEGREES_DD_PATH'); Kind = 'digit' }
        @{ Line = '    51DEGREES_DD_PATH_OTHER'; Allowed = @('51DEGREES_DD_PATH'); Kind = 'digit' }
        @{ Line = 'DATA_FILE_ENV_VAR = "51DEGREES_DD_PATH"'; Allowed = @(); Kind = 'digit' }
    ) {
        @(Find-EnvironmentNameProblem $Line $Allowed | ForEach-Object { $_.Kind }) |
            Should -Contain $Kind
    }
}

Describe 'Get-FallbackName' {

    It 'lets <Path> hold <Name>' -ForEach @(
        @{ Path = 'pipeline/fiftyone_pipeline_did/tox.ini'; Name = 'FOD_CLOUD_API_URL' }
        @{ Path = 'device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py'; Name = '51DEGREES_DD_PATH' }
        @{ Path = 'device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py'; Name = 'cloud_endpoint' }
        @{ Path = 'ip-intelligence/fiftyone_ipintelligence_examples/src/fiftyone_ipintelligence_examples/example_utils.py'; Name = 'IPINTELLIGENCEDATAFILE' }
        @{ Path = 'pipeline/fiftyone_pipeline_cloudrequestengine/src/fiftyone_pipeline_cloudrequestengine/constants.py'; Name = 'FOD_CLOUD_API_URL' }
        @{ Path = 'pipeline/fiftyone_pipeline_cloudrequestengine/readme.md'; Name = 'FOD_CLOUD_API_URL' }
        @{ Path = 'pipeline/fiftyone_pipeline_did/src/fiftyone_pipeline_did/did_client.py'; Name = 'FOD_CLOUD_API_URL' }
        @{ Path = 'pipeline/fiftyone_pipeline_did/tests/test_live_cloud.py'; Name = 'resource_key' }
    ) {
        @(Get-FallbackName $Path) | Should -Contain $Name
    }

    It 'does not let <Path> hold <Name>' -ForEach @(
        @{ Path = 'pipeline/fiftyone_pipeline_did/tox.ini'; Name = '51DEGREES_DD_PATH' }
        @{ Path = 'pipeline/fiftyone_pipeline_did/src/fiftyone_pipeline_did/did_client.py'; Name = 'resource_key' }
        @{ Path = 'pipeline/fiftyone_pipeline_cloudrequestengine/src/fiftyone_pipeline_cloudrequestengine/constants.py'; Name = '51DEGREES_DD_PATH' }
        @{ Path = 'ip-intelligence/fiftyone_ipintelligence_examples/src/fiftyone_ipintelligence_examples/example_utils.py'; Name = '51DEGREES_DD_PATH' }
        @{ Path = 'device-detection/fiftyone_devicedetection_examples/src/fiftyone_devicedetection_examples/example_utils.py'; Name = 'IPINTELLIGENCEDATAFILE' }
    ) {
        @(Get-FallbackName $Path) | Should -Not -Contain $Name
    }

    It 'lets <Path> hold no old name' -ForEach @(
        @{ Path = 'ci/run-unit-tests.ps1' }
        @{ Path = 'readme.md' }
        @{ Path = 'pipeline/fiftyone_pipeline_core/src/fiftyone_pipeline_core/pipeline.py' }
        @{ Path = 'pipeline/fiftyone_pipeline_core/readme.md' }
        @{ Path = 'device-detection/fiftyone_devicedetection_examples/tests/test_cloudexamples.py' }
        @{ Path = 'device-detection/ci/run-integration-tests.ps1' }
        @{ Path = 'pipeline/fiftyone_pipeline_did/tests/test_did_client_live.py' }
        @{ Path = 'location/examples/cloud/gettingstarted.py' }
        @{ Path = 'some/new/package/tox.ini' }
        @{ Path = 'some/new/example_utils.py' }
    ) {
        @(Get-FallbackName $Path) | Should -BeNullOrEmpty
    }
}

# Tests for ci/check-environment-variable-names.ps1.
#
# Each case is one line of text and what the check must make of it. The names
# that must fail are made up for these tests.

BeforeAll {
    . (Join-Path $PSScriptRoot 'check-environment-variable-names.ps1')
}

Describe 'Find-EnvironmentNameProblem' {

    It 'finds <Name> read or set in <Line>' -ForEach @(
        @{ Line = 'os.environ.get("EXAMPLE_SETTING")'; Name = 'EXAMPLE_SETTING' }
        @{ Line = "os.environ.get('example_setting', 'none')"; Name = 'example_setting' }
        @{ Line = 'os.environ["EXAMPLE_SETTING"] = "value"'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'saved = os.environ.pop("EXAMPLE_SETTING", None)'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'os.environ.setdefault("EXAMPLE_SETTING", "value")'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'value = os.getenv("EXAMPLE_SETTING")'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'if "example_setting" in os.environ:'; Name = 'example_setting' }
        @{ Line = 'if "EXAMPLE_SETTING" not in os.environ:'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'monkeypatch.setenv("EXAMPLE_SETTING", "value")'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'monkeypatch.delenv("EXAMPLE_SETTING", raising=False)'; Name = 'EXAMPLE_SETTING' }
        @{ Line = '$env:EXAMPLE_SETTING = "value"'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'if (!$Env:Example_Setting) {'; Name = 'Example_Setting' }
        @{ Line = '${env:EXAMPLE_SETTING} = "value"'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'Remove-Item Env:EXAMPLE_SETTING'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'Remove-Item Env:\EXAMPLE_SETTING'; Name = 'EXAMPLE_SETTING' }
        @{ Line = '[Environment]::SetEnvironmentVariable("EXAMPLE_SETTING", $value)'; Name = 'EXAMPLE_SETTING' }
        @{ Line = '[Environment]::GetEnvironmentVariable("EXAMPLE_SETTING")'; Name = 'EXAMPLE_SETTING' }
        @{ Line = '          url: ${{ env.EXAMPLE_SETTING }}'; Name = 'EXAMPLE_SETTING' }
        @{ Line = 'export EXAMPLE_SETTING=value'; Name = 'EXAMPLE_SETTING' }
        # A name has to start with the underscore and be in upper case.
        @{ Line = 'os.environ.get("51DEGREES_EXAMPLE_SETTING")'; Name = '51DEGREES_EXAMPLE_SETTING' }
        @{ Line = '$env:_51degrees_example_setting = "value"'; Name = '_51degrees_example_setting' }
        @{ Line = 'os.environ.get("EXAMPLE_51DEGREES_SETTING")'; Name = 'EXAMPLE_51DEGREES_SETTING' }
    ) {
        @(Find-EnvironmentNameProblem $Line) | Should -Be @($Name)
    }

    It 'finds each name once in <Line>' -ForEach @(
        @{ Line = 'a = os.environ.get("_51DEGREES_EXAMPLE_SETTING") or os.environ.get("EXAMPLE_SETTING") or os.environ.get("OTHER_SETTING")'
           Names = @('EXAMPLE_SETTING', 'OTHER_SETTING') }
        @{ Line = '$env:EXAMPLE_SETTING = $env:EXAMPLE_SETTING + $env:TEMP'
           Names = @('EXAMPLE_SETTING') }
    ) {
        @(Find-EnvironmentNameProblem $Line) | Should -Be $Names
    }

    It 'leaves <Line> alone, as its name starts _51DEGREES_' -ForEach @(
        @{ Line = 'os.environ.get("_51DEGREES_EXAMPLE_SETTING")' }
        @{ Line = 'os.environ["_51DEGREES_EXAMPLE_SETTING"] = "value"' }
        @{ Line = 'if "_51DEGREES_EXAMPLE_SETTING" in os.environ:' }
        @{ Line = '$env:_51DEGREES_EXAMPLE_SETTING = "value"' }
        @{ Line = '${env:_51DEGREES_EXAMPLE_SETTING} = $value' }
        @{ Line = 'Remove-Item Env:_51DEGREES_EXAMPLE_SETTING' }
        @{ Line = 'export _51DEGREES_EXAMPLE_SETTING=value' }
        @{ Line = '          url: ${{ env._51DEGREES_EXAMPLE_SETTING }}' }
    ) {
        @(Find-EnvironmentNameProblem $Line) | Should -BeNullOrEmpty
    }

    It 'leaves <Line> alone, as the platform defines its name' -ForEach @(
        @{ Line = 'in_actions = os.environ.get("GITHUB_ACTIONS") == "true"' }
        @{ Line = 'if ($env:GITHUB_JOB -eq "Test") {' }
        @{ Line = '"key=value" >> $env:GITHUB_OUTPUT' }
        @{ Line = '$env:TEMP = New-Item -ItemType Directory -Force -Path "C:\tmp"' }
        @{ Line = '$env:TMP = $env:TEMP' }
        @{ Line = '$env:PYTEST_ADDOPTS = "$addopts -m `"not live`"".Trim()' }
        @{ Line = '$env:PYTHONPATH = Join-Path $PWD ''src''' }
        @{ Line = 'export FLASK_APP=app.py' }
        @{ Line = '$env:PATH = "$bin;$env:Path"' }
    ) {
        @(Find-EnvironmentNameProblem $Line) | Should -BeNullOrEmpty
    }

    # A setting, a parameter and a request's own environ are not environment
    # variables of the process.
    It 'leaves <Line> alone, as it reads or sets no environment variable' -ForEach @(
        @{ Line = 'pipeline_settings["cloud_endpoint"] = cloud_endpoint' }
        @{ Line = 'builder = Builder({"resource_key": "YOUR_RESOURCE_KEY"})' }
        @{ Line = 'Builder(resource_key=key, license_key=licence)' }
        @{ Line = 'def run(self, resource_key, logger, cloud_endpoint = None):' }
        @{ Line = 'EXAMPLE_SETTING = "example_setting"' }
        @{ Line = 'raw = request.environ.get("RAW_URI")' }
        @{ Line = 'env.pop("EXAMPLE_SETTING", None)' }
        @{ Line = 'environment = dict(os.environ, EXAMPLE_SETTING=value)' }
        @{ Line = 'pass_env = EXAMPLE_SETTING' }
        @{ Line = 'Set the 51D_ cookie for the 51Did example.' }
        @{ Line = '        env:' }
    ) {
        @(Find-EnvironmentNameProblem $Line) | Should -BeNullOrEmpty
    }
}

Describe 'Find-EnvironmentNameProblem in a workflow' {

    It 'finds <Name>, a key of an env map, in <Line>' -ForEach @(
        @{ Line = '          EXAMPLE_SETTING: ${{ github.workspace }}/folder'; Name = 'EXAMPLE_SETTING' }
        @{ Line = '      EXAMPLE_SETTING: value'; Name = 'EXAMPLE_SETTING' }
    ) {
        @(Find-EnvironmentNameProblem $Line '.github/workflows/example.yml') |
            Should -Be @($Name)
    }

    It 'leaves <Line> alone' -ForEach @(
        @{ Line = '          _51DEGREES_EXAMPLE_SETTING: ${{ secrets._51DEGREES_EXAMPLE_SETTING }}' }
        @{ Line = '          GITHUB_TOKEN: ${{ github.token }}' }
        @{ Line = '        uses: actions/checkout@v4' }
        @{ Line = '    runs-on: ubuntu-latest' }
        @{ Line = '        shell: pwsh' }
    ) {
        @(Find-EnvironmentNameProblem $Line '.github/workflows/example.yml') |
            Should -BeNullOrEmpty
    }

    It 'reads a key of a map only in a workflow, so <Path> is left alone' -ForEach @(
        @{ Path = 'ci/packages.json' }
        @{ Path = 'device-detection/readme.md' }
        @{ Path = '' }
    ) {
        @(Find-EnvironmentNameProblem '    EXAMPLE_SETTING: value' $Path) |
            Should -BeNullOrEmpty
    }
}

Describe 'Test-EnvironmentName' {

    It 'takes <Name>' -ForEach @(
        @{ Name = '_51DEGREES_EXAMPLE_SETTING' }
        @{ Name = 'GITHUB_ENV' }
        @{ Name = 'TEMP' }
        @{ Name = 'PSModulePath' }
    ) {
        Test-EnvironmentName $Name | Should -BeTrue
    }

    It 'refuses <Name>' -ForEach @(
        @{ Name = 'EXAMPLE_SETTING' }
        @{ Name = '_51degrees_example_setting' }
        @{ Name = '51DEGREES_EXAMPLE_SETTING' }
        @{ Name = 'TEMPORARY' }
        @{ Name = 'MY_GITHUB_SETTING' }
    ) {
        Test-EnvironmentName $Name | Should -BeFalse
    }
}

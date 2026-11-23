Set-Location -Path "..\fiftyone_ipintelligence_onpremise\"

# Check if _IpIntelligenceEngineModule.pyd exists and delete it if it does
if (Test-Path -Path ".\src\fiftyone_ipintelligence_onpremise\_IpIntelligenceEngineModule.pyd") {
    Remove-Item ".\src\fiftyone_ipintelligence_onpremise\_IpIntelligenceEngineModule.pyd"
}

# Build the module
python setup.py build_clib build_ext --inplace

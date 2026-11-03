Set-Location -Path "..\fiftyone_devicedetection_onpremise\"

# Check if _DeviceDetectionHashEngineModule.pyd exists and delete it if it does
if (Test-Path -Path ".\src\fiftyone_devicedetection_onpremise\_DeviceDetectionHashEngineModule.pyd") {
    Remove-Item ".\src\fiftyone_devicedetection_onpremise\_DeviceDetectionHashEngineModule.pyd"
}

# Build the module
python setup.py build_clib build_ext --inplace

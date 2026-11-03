# Check swig exists
try{if(Get-Command swig){
    "Using swig:"
    swig -version
}}
Catch {"Cannot reach swig command, make sure swig 4.0+ is installed and added to PATH"}

python -m pip install -r requirements.txt

Set-Location -Path fiftyone_devicedetection_onpremise/
Get-Location

python setup.py build_clib build_ext

Set-Location -Path ../ 
Get-Location

python -m pip install -e fiftyone_devicedetection_shared/
python -m pip install -e fiftyone_devicedetection_cloud/
python -m pip install -e fiftyone_devicedetection_onpremise/
python -m pip install -e fiftyone_devicedetection/
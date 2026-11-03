PACKAGES = fiftyone_devicedetection_shared/ fiftyone_devicedetection_cloud/ fiftyone_devicedetection_onpremise/ fiftyone_devicedetection/ 

all: install

init:
	cd ./fiftyone_devicedetection_onpremise/ &&pwd && python setup.py build_clib build_ext --inplace && cd .. && pwd
	
install: init $(PACKAGES)
	python -m pip install -e $(PACKAGES)

test:

.PHONY: clean
clean:
	find -type f -name '*.o' | xargs rm
	find -type f -name '*.a' | xargs rm
	find -type f -name '*.so' | xargs rm
	rm fiftyone_devicedetection_onpremise/dist/*.egg

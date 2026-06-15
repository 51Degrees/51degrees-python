PACKAGES = fiftyone_ipintelligence_shared/ fiftyone_ipintelligence_cloud/ fiftyone_ipintelligence_onpremise/ fiftyone_ipintelligence/

all: install

init:
	cd ./fiftyone_ipintelligence_onpremise/ &&pwd && python setup.py build_clib build_ext --inplace && cd .. && pwd

install: init $(PACKAGES)
	python -m pip install -e $(PACKAGES)

test:

.PHONY: clean
clean:
	find -type f -name '*.o' | xargs rm
	find -type f -name '*.a' | xargs rm
	find -type f -name '*.so' | xargs rm
	rm fiftyone_ipintelligence_onpremise/dist/*.egg

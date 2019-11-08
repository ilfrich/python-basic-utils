deploy:
	python setup.py sdist bdist_wheel upload -r artifactory

local-install: local-uninstall
	sudo python3.6 setup.py develop

local-uninstall:
	sudo python3.6 setup.py develop --uninstall

clean:
	rm -f dist/python-basic-utils*

test:
	pytest

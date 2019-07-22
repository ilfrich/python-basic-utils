deploy:
	python setup.py sdist bdist_wheel upload -r artifactory

local-install:
	python3 setup.py sdist
	sudo pip3 install dist/python-basic-utils-0.2.1.tar.gz

clean:
	rm -f dist/python-basic-utils*

test:
	pytest

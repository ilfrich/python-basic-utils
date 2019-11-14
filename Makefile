deploy:
	python setup.py sdist bdist_wheel upload

local-install: local-uninstall
	sudo python3.6 setup.py develop

local-uninstall:
	sudo python3.6 setup.py develop --uninstall

clean:
	rm -f dist/pbu-*

test:
	pytest

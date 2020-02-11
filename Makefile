deploy: clean
	python3 setup.py sdist bdist_wheel && python3 -m twine upload dist/*

local-install: local-uninstall
	sudo python3.6 setup.py develop

local-uninstall:
	sudo python3.6 setup.py develop --uninstall

clean:
	rm -f dist/pbu-*

test:
	pytest

deploy: clean
	python3 setup.py sdist bdist_wheel && python3 -m twine upload dist/*

local-install: local-uninstall
	python setup.py develop --user

local-uninstall:
	python setup.py develop --uninstall --user

clean:
	rm -f dist/pbu-*

test:
	pytest

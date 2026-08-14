deploy: clean
	python3.11 setup.py sdist bdist_wheel && python3.11 -m twine upload dist/*

local-install: local-uninstall
	pip3.11 install -e .

local-uninstall:
	pip3.11 uninstall -y pbu

clean:
	rm -f dist/pbu-*

test:
	pytest

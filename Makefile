all:
	./setup.py install --user

pypi:
	./setup.py sdist upload -r pypi

clean:
	rm -r build dist *.egg-info *.pyc
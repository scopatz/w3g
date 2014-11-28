all:
	./setup.py install --user

clean:
	rm -r build dist *.egg-info *.pyc
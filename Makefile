all:
	./setup.py install --user

pypi:
	./setup.py sdist upload -r pypi

conda:
	export PATH=/home/scopatz/miniconda/bin:$PATH
	conda build --no-binstar-upload .
	binstar upload -u scopatz /home/scopatz/miniconda/conda-bld/linux-64/w3g*.tar.bz2

clean:
	rm -r build dist *.egg-info *.pyc
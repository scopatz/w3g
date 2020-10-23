#!/usr/bin/env python
try:
    from setuptools import setup
    have_setuptools = True
except ImportError:
    from distutils.cor import setup
    have_setuptools = False

def main():
    with open('readme.rst') as f:
        longdesc = f.read()
    kw = dict(
        name='w3g',
        py_modules=['w3g'],
        version='1.0.5',
        long_description=longdesc,
        author="Anthony Scopatz",
        author_email="scopatz@gmail.com",
        description="Access Warcraft 3 replay files from Python 2 or 3.",
        license="CC0",
        data_files=[("", ['license', 'readme.rst']),],
        )
    if have_setuptools:
        kw['entry_points'] = {'console_scripts': ['w3g = w3g:main']}
    setup(**kw)

if __name__ == '__main__':
    main()

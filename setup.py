from setuptools import setup, find_packages
from codecs import open
from os import path

readme = 'A package to use tobii eye tracking with psychopy.'
if path.isfile('README.md'):
    readme = open('README.md', 'r').read()

version = '0.1.0'

setup(
    name='tobii-psychopy',
    version=version,
    description='A package to use tobii eye tracking with psychopy.',
    long_description=readme,
    url='https://github.com/janfreyberg/tobii-psychopy',
    download_url='https://github.com/janfreyberg/tobii-psychopy/tarball/' +
        version,
    # Author details
    author='Jan Freyberg',
    author_email='jan.freyberg@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Code Generators',
        'License :: OSI Approved :: MIT License',
        # Only the following because these work w/ psychopy
        'Programming Language :: Python :: 2.7',
    ],
    keywords=['tobii', 'eyetracking', 'gazetracking'],
    packages=['tobii-psychopy'],
    install_requires=['numpy', 'psychopy', 'datetime'],
    # package_data={
    #     '': ['templates/*.tpl']
    # },
)

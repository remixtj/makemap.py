# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path, walk

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

package_data_files = []
for root, dirs, files in walk(path.join(here, 'makemappy/mappina')):
    relative_root = root.replace(path.join(here, 'makemappy/'),'')
    for file in files:
        package_data_files.append(path.join(relative_root, file))

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='makemap.py',  

    version='1.0.0',  

    description='Converts a GPX file recorded with a GPS into an html report, with optional photo georeferencing', 

    long_description=long_description,

    url='https://github.com/remixtj/makemap.py',  

    author='Luca \'remix_tj\' Lorenzetto',

    author_email='lorenzetto.luca@gmail.com',  

    keywords='gpx mountain',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']), 

    install_requires=['gpxpy', 'exifread', 'jinja2', 'pytz', 'Pillow', 'matplotlib' ],  # Optional


    # If there are data files included in your packages that need to be
    # installed, specify them here.
    #
    # If using Python 2.6 or earlier, then these have to be included in
    # MANIFEST.in as well.
    package_data={  # Optional
        'makemappy': package_data_files
    },

    entry_points={  # Optional
        'console_scripts': [
            'makemappy=makemappy:main',
        ],
    },
)

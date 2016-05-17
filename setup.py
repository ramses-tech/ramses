import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
VERSION = open(os.path.join(here, 'VERSION')).read()

requires = [
    'cryptacular',
    'inflection',
    'nefertari>=0.7.0',
    'pyramid',
    'ramlfications==0.1.8',
    'six',
    'transaction',
]

setup(name='ramses',
      version=VERSION,
      description='Generate a RESTful API for Pyramid using RAML',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Framework :: Pyramid",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      author='Brandicted',
      author_email='hello@ramses.tech',
      url='https://github.com/ramses-tech/ramses',
      keywords='web pyramid pylons ramses raml',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="ramses",
      entry_points="""\
        [pyramid.scaffold]
            ramses_starter = ramses.scaffolds:RamsesStarterTemplate
      """)

from setuptools import setup, find_packages
import sys, os

version = '4.0'

setup(name='rhythmbox-gmusic',
      version=version,
      description="Rhythmbox Google Play Music Plugin",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Vladimir Iakovlev',
      author_email='nvbn.rm@gmail.com',
      url='https://github.com/nvbn/rhythmbox-gmusic/',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'gmusicapi',
          'futures',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      data_files=[
        ('/usr/lib/rhythmbox/plugins/googleplaymusic', ['googleplaymusic.plugin']),
        ('/usr/share/locale/ru/LC_MESSAGES/', ['po/ru/rhythmbox-gmusic.po']),
      ]
      )

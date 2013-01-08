Rhythmbox Google Play Music Plugin
==================================
Plugin for playing music from Google Play Music in Rhythmbox.


Installation
============
For ubuntu user `ppa <https://launchpad.net/~nvbn-rm/+archive/ppa>`_:

``add-apt-repository ppa:nvbn-rm/ppa``

``apt-get update``

``apt-get install rhythmbox-gmusic`` 

The gmusicapi Python package is needed for the plugin to work. You can install it with:
``sudo apt-get install python-pip``
``sudo pip install gmusicapi``

Developers can clone this repository and install via ``setup.py``

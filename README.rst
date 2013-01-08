Rhythmbox Google Play Music Plugin
==================================
Plugin for playing music from Google Play Music in Rhythmbox.


Installation
============
For Ubuntu users, `ppa <https://launchpad.net/~nvbn-rm/+archive/ppa>`_::

    sudo add-apt-repository ppa:nvbn-rm/ppa
    sudo apt-get update
    sudo apt-get install rhythmbox-gmusic

For Fedora users, installation via PIP::

    sudo yum install python-pip git
    sudo pip-python install git+https://github.com/nvbn/rhythmbox-gmusic.git#rhythmbox-gmusic

The gmusicapi Python package is needed for the plugin to work. You can install it with::

    sudo apt-get install python-pip
    sudo pip install gmusicapi

Developers can clone this repository and install via ``setup.py``

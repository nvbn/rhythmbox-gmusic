Rhythmbox Google Play Music Plugin
==================================
Plugin for playing music from Google Play Music in Rhythmbox 2.x.


Installation
============

Ubuntu Installation via PPA
---------------------------

Use the `PPA <https://launchpad.net/~nvbn-rm/+archive/ppa>`_::

    sudo add-apt-repository ppa:nvbn-rm/ppa
    sudo apt-get update
    sudo apt-get install rhythmbox-gmusic

The Rhythmbox plugin requires the gmusicapi Python package. You can install it with::

    sudo apt-get install python-pip
    sudo pip install gmusicapi

For Ubuntu 14.xx or Later Users
```````````````````````````````

Canonical's repos package Rhythmbox 3 beginning with Ubuntu 14.04 Trusty Tahr. If you are running Ubuntu 14 or later, you will need to add the Saucy repos to your sources, and downgrade to Rhythmbox 2.99 to use this plugin. Open ``/etc/apt/sources.list`` with elevated permissions (e.g. ``sudo emacs`` or ``gksudo gedit``) and add or uncomment these lines::

    deb http://us.archive.ubuntu.com/ubuntu/ saucy main restricted
    deb-src http://us.archive.ubuntu.com/ubuntu/ saucy main restricted

Then add the PPA as described above (if you haven't already) and run::

    sudo apt-get update
    sudo apt-get remove rhythmbox
    sudo apt-get install rhythmbox=2.99.1-0ubuntu1


Ubuntu Installation via PIP
---------------------------

From the shell::

    sudo apt-get install python-pip git-core
    sudo pip install git+https://github.com/nvbn/rhythmbox-gmusic.git#egg=rhythmbox-gmusic


Fedora Installation via PIP
---------------------------

From the shell::

    sudo dnf install python-pip git
    sudo pip install git+https://github.com/nvbn/rhythmbox-gmusic.git#egg=rhythmbox-gmusic


Developers
==========
Developers can clone this repository and install via ``setup.py`` or add the ``-e`` to any PIP-based installation to get an editable git clone.

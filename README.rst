Rhythmbox Google Play Music Plugin
==================================
Plugin for playing music from Google Play Music in Rhythmbox.


Ubuntu Installation via PPA
===========================
Use the `PPA <https://launchpad.net/~nvbn-rm/+archive/ppa>`_::

    sudo add-apt-repository ppa:nvbn-rm/ppa
    sudo apt-get update
    sudo apt-get install rhythmbox-gmusic

The Rhythmbox plugin requires the gmusicapi Python package. You can install it with::

    sudo apt-get install python-pip
    sudo pip install gmusicapi


Ubuntu Installation via PIP
===========================

    sudo apt-get install python-pip git-core
    sudo pip install git+https://github.com/nvbn/rhythmbox-gmusic.git#egg=rhythmbox-gmusic


Fedora Installation via PIP
===========================

    sudo yum install python-pip git
    sudo pip-python install git+https://github.com/nvbn/rhythmbox-gmusic.git#egg=rhythmbox-gmusic


Developers
==========
Developers can clone this repository and install via ``setup.py`` or add the ``-e`` to any PIP-based installation to get an editable git clone.

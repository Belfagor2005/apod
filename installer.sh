#!/bin/bash
## setup command=wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/apod/main/installer.sh -O - | /bin/sh

version='1.6'
changelog='\nRecoded structure for player video'
TMPPATH=/tmp/apod-main
FILEPATH=/tmp/main.tar.gz

if [ ! -d /usr/lib64 ]; then
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/apod
else
    PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/apod
fi

if [ -f /var/lib/dpkg/status ]; then
    STATUS=/var/lib/dpkg/status
    OSTYPE=DreamOs
else
    STATUS=/var/lib/opkg/status
    OSTYPE=Dream
fi
echo ""

if [ -f /usr/bin/wget ]; then
    echo "wget exist"
else
    if [ $OSTYPE = "DreamOs" ]; then
        apt-get update && apt-get install wget
    else
        opkg update && opkg install wget
    fi
fi

if python --version 2>&1 | grep -q '^Python 3\.'; then
    PYTHON=PY3
    Packagesix=python3-six
    Packagerequests=python3-requests
else
    PYTHON=PY2
    Packagerequests=python-requests
fi

if [ $PYTHON = "PY3" ]; then
    if grep -qs "Package: $Packagesix" $STATUS ; then
        echo ""
    else
        opkg update && opkg install python3-six
    fi
fi
echo ""
if grep -qs "Package: $Packagerequests" $STATUS ; then
    echo ""
else
    echo "Need to install $Packagerequests"
    echo ""
    if [ $OSTYPE = "DreamOs" ]; then
        apt-get update && apt-get install python-requests -y
    elif [ $PYTHON = "PY3" ]; then
        opkg update && opkg install python3-requests
    elif [ $PYTHON = "PY2" ]; then
        opkg update && opkg install python-requests
    fi
fi
echo ""

mkdir -p $TMPPATH
cd $TMPPATH
set -e

if [ -f /var/lib/dpkg/status ]; then
    echo "# Your image is OE2.5/2.6 #"
    echo ""
else
    echo "# Your image is OE2.0 #"
    echo ""
fi

if [ $OSTYPE != "DreamOs" ]; then
    opkg update && opkg install ffmpeg gstplayer exteplayer3 enigma2-plugin-systemplugins-serviceapp python3-youtube-dl
fi
sleep 2

wget --no-check-certificate 'https://github.com/Belfagor2005/apod/archive/refs/heads/main.tar.gz' -O $FILEPATH || { echo "Download failed"; exit 1; }
tar -xzf $FILEPATH -C /tmp/ || { echo "Extraction failed"; exit 1; }
cp -r /tmp/apod-main/usr/ / || { echo "Copy failed"; exit 1; }
set +e
cd
sleep 2

if [ ! -d $PLUGINPATH ]; then
    echo "Some thing wrong .. Plugin not installed"
    rm -rf $TMPPATH > /dev/null 2>&1
    exit 1
fi
rm -rf $TMPPATH > /dev/null 2>&1
rm -f $FILEPATH > /dev/null 2>&1
sync

FILE="/etc/image-version"
box_type=$(head -n 1 /etc/hostname)
distro_value=$(grep '^distro=' "$FILE" | awk -F '=' '{print $2}')
distro_version=$(grep '^version=' "$FILE" | awk -F '=' '{print $2}')
python_vers=$(python --version 2>&1)
echo "#########################################################
#          	    INSTALLED SUCCESSFULLY                  #
#                developed by LULULLA                   #
#               https://corvoboys.org                   #
#########################################################
#           your Device will RESTART Now                #
#########################################################
^^^^^^^^^^Debug information:
BOX MODEL: $box_type
OO SYSTEM: $OSTYPE
PYTHON: $python_vers
IMAGE NAME: $distro_value
IMAGE VERSION: $distro_version"

sleep 5
killall -9 enigma2
exit 0
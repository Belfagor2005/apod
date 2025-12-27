#!/bin/bash
## setup command=wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/apod/main/installer.sh -O - | /bin/sh

version='1.8'
changelog='Fix Sonar sign'
TMPPATH=/tmp/apod-install
FILEPATH=/tmp/apod-main.tar.gz

echo "Starting APOD (Astronomy Picture of the Day) installation..."

# Determine plugin path based on architecture
if [ ! -d /usr/lib64 ]; then
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/apod
else
    PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/apod
fi

# Cleanup function
cleanup() {
    echo "Cleaning up temporary files..."
    [ -d "$TMPPATH" ] && rm -rf "$TMPPATH"
    [ -f "$FILEPATH" ] && rm -f "$FILEPATH"
}

# Detect OS type
detect_os() {
    if [ -f /var/lib/dpkg/status ]; then
        OSTYPE="DreamOs"
        STATUS="/var/lib/dpkg/status"
    elif [ -f /etc/opkg/opkg.conf ] || [ -f /var/lib/opkg/status ]; then
        OSTYPE="OE"
        STATUS="/var/lib/opkg/status"
    else
        OSTYPE="Unknown"
        STATUS=""
    fi
    echo "Detected OS type: $OSTYPE"
}

detect_os

# Cleanup before starting
cleanup
mkdir -p "$TMPPATH"

# Install wget if missing
if ! command -v wget >/dev/null 2>&1; then
    echo "Installing wget..."
    case "$OSTYPE" in
        "DreamOs")
            apt-get update && apt-get install -y wget || { echo "Failed to install wget"; exit 1; }
            ;;
        "OE")
            opkg update && opkg install wget || { echo "Failed to install wget"; exit 1; }
            ;;
        *)
            echo "Unsupported OS type. Cannot install wget."
            exit 1
            ;;
    esac
else
    echo "wget is available"
fi

# Detect Python version
if python --version 2>&1 | grep -q '^Python 3\.'; then
    echo "Python3 image detected"
    PYTHON="PY3"
    Packagesix="python3-six"
    Packagerequests="python3-requests"
else
    echo "Python2 image detected"
    PYTHON="PY2"
    Packagerequests="python-requests"
    Packagesix="python-six"
fi

# Install required packages
install_pkg() {
    local pkg=$1
    if [ -z "$STATUS" ] || ! grep -qs "Package: $pkg" "$STATUS" 2>/dev/null; then
        echo "Installing $pkg..."
        case "$OSTYPE" in
            "DreamOs")
                apt-get update && apt-get install -y "$pkg" || { echo "Could not install $pkg, continuing anyway..."; }
                ;;
            "OE")
                opkg update && opkg install "$pkg" || { echo "Could not install $pkg, continuing anyway..."; }
                ;;
            *)
                echo "Cannot install $pkg on unknown OS type, continuing..."
                ;;
        esac
    else
        echo "$pkg already installed"
    fi
}

# Install Python dependencies
if [ "$PYTHON" = "PY3" ]; then
    install_pkg "$Packagesix"
fi
install_pkg "$Packagerequests"

# Install additional multimedia packages for OE systems
if [ "$OSTYPE" = "OE" ]; then
    echo "Installing additional multimedia packages..."
    for pkg in ffmpeg gstplayer exteplayer3 enigma2-plugin-systemplugins-serviceapp; do
        install_pkg "$pkg"
    done
    
    # Install youtube-dl based on Python version
    if [ "$PYTHON" = "PY3" ]; then
        install_pkg "python3-youtube-dl" || install_pkg "yt-dlp"
    else
        install_pkg "python-youtube-dl"
    fi
fi

# Download and extract
echo "Downloading APOD..."
wget --no-check-certificate 'https://github.com/Belfagor2005/apod/archive/refs/heads/main.tar.gz' -O "$FILEPATH"
if [ $? -ne 0 ]; then
    echo "Failed to download APOD package!"
    cleanup
    exit 1
fi

echo "Extracting package..."
tar -xzf "$FILEPATH" -C "$TMPPATH"
if [ $? -ne 0 ]; then
    echo "Failed to extract APOD package!"
    cleanup
    exit 1
fi

# Install plugin files
echo "Installing plugin files..."
mkdir -p "$PLUGINPATH"

# Find correct directory in extracted structure
if [ -d "$TMPPATH/apod-main/usr/lib/enigma2/python/Plugins/Extensions/apod" ]; then
    cp -r "$TMPPATH/apod-main/usr/lib/enigma2/python/Plugins/Extensions/apod"/* "$PLUGINPATH/" 2>/dev/null
    echo "Copied from standard plugin directory"
elif [ -d "$TMPPATH/apod-main/usr/lib64/enigma2/python/Plugins/Extensions/apod" ]; then
    cp -r "$TMPPATH/apod-main/usr/lib64/enigma2/python/Plugins/Extensions/apod"/* "$PLUGINPATH/" 2>/dev/null
    echo "Copied from lib64 plugin directory"
elif [ -d "$TMPPATH/apod-main/usr" ]; then
    # Copy entire usr tree
    cp -r "$TMPPATH/apod-main/usr"/* /usr/ 2>/dev/null
    echo "Copied entire usr structure"
else
    echo "Could not find plugin files in extracted archive"
    echo "Available directories in tmp:"
    find "$TMPPATH" -type d | head -10
    cleanup
    exit 1
fi

sync

# Verify installation
echo "Verifying installation..."
if [ -d "$PLUGINPATH" ] && [ -n "$(ls -A "$PLUGINPATH" 2>/dev/null)" ]; then
    echo "Plugin directory found and not empty: $PLUGINPATH"
    echo "Contents:"
    ls -la "$PLUGINPATH/" | head -10
else
    echo "Plugin installation failed or directory is empty!"
    cleanup
    exit 1
fi

# Cleanup
cleanup
sync

# System info
FILE="/etc/image-version"
box_type=$(head -n 1 /etc/hostname 2>/dev/null || echo "Unknown")
distro_value=$(grep '^distro=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
distro_version=$(grep '^version=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
python_vers=$(python --version 2>&1)

cat <<EOF

#########################################################
#          	    INSTALLED SUCCESSFULLY                  #
#                developed by LULULLA                   #
#               https://corvoboys.org                   #
#########################################################
#           your Device will RESTART Now                #
#########################################################
Debug information:
BOX MODEL: $box_type
OS SYSTEM: $OSTYPE
PYTHON: $python_vers
IMAGE NAME: ${distro_value:-Unknown}
IMAGE VERSION: ${distro_version:-Unknown}
PLUGIN VERSION: $version
EOF

echo "Restarting enigma2 in 5 seconds..."
sleep 5
killall -9 enigma2
exit 0
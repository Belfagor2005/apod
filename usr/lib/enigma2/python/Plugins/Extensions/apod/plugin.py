# -*- coding: utf-8 -*-
from __future__ import print_function

"""
#########################################################
#                                                       #
#  APOD - Astronomy Picture of the Day Plugin           #
#  Version: 1.7                                         #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0                             #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#  Last Modified: "16:45 - 20251122"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  - API integration with                               #
#    NASA's Astronomy Picture of the Day API            #
#  - Image downloader                                   #
#  - Image display and handling                         #
#  - Data caching system                                #
#  - Custom settings configuration                      #
#  - Advanced error logging                             #
#  - User interface and display components              #
#  - Security enhancements & URL validation             #
#  - Multi-format image support (JPG/PNG/GIF/TIFF)      #
#  - Animated GIF support                               #
#  - YouTube video playback                             #
#  - Smart cache management                             #
#  - API key file management                            #
#                                                       #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""
__author__ = "Lululla"

from datetime import date
import logging
from json import dump as json_dump, load as json_load
from os import listdir, makedirs, remove
from os.path import basename, exists, getmtime, getsize, join, splitext
from re import search
from shutil import copyfileobj
from urllib.parse import urlparse

import requests
from twisted.internet import reactor, threads
from twisted.web.client import downloadPage
from enigma import eServiceReference, eTimer, getDesktop
from Components.ActionMap import HelpableActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.config import (
    ConfigSelection,
    ConfigSubsection,
    ConfigText,
    config,
    getConfigListEntry
)

from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from Tools.LoadPixmap import LoadPixmap

from . import _

screen_width = getDesktop(0).size().width()
"""
---

### **How to Use the NASA API Key for the APOD Plugin**
#### **1. Obtain the NASA API Key**
To access the Astronomy Picture of the Day (APOD) data from NASA, you need a valid API key.

* Visit the NASA API registration page:
    https://api.nasa.gov/`

* After completing the registration, you will receive a unique API key that grants access to the data.
---

#### **2. Adding the API Key to Your System**
Once you have the API key, store it securely on your system.

##### **Method 1: Create a file for the API Key**
Run this command in your terminal to create the file:

```bash
echo "YOUR_NASA_API_KEY" > /etc/apod_api_key
```

Set proper permissions so only the owner can read/write:

```bash
chmod 600 /etc/apod_api_key
```

Make sure the file is accessible and secure.

---

#### **3. Restart the System to Apply Changes**
After saving the API key, restart the plugin or GUI so the key can be loaded correctly.

---

#### **4. Troubleshooting**
* **Invalid API Key Error**: Check the contents of your key file and ensure the key is copied exactly as provided.
* **Permission Issues**: Ensure the key file has the correct permissions (`chmod 600`).
* **Missing File**: Make sure the key exists in one of the expected paths.
---
Once done, the plugin should be able to access NASA's APOD data and display the Astronomy Picture of the Day properly. ✨
---

"""


currversion = '1.8'
title_plug = 'Picture of The Day - Nasa %s by %s' % (currversion, __author__)
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
CACHE_DIR = "/tmp/apod_cache/"

if not exists(CACHE_DIR):
    makedirs(CACHE_DIR)

TMP_IMG_PNG = join(CACHE_DIR, "apod.png")
TMP_IMG_JPG = join(CACHE_DIR, "apod.jpg")
TMP_IMG_GIF = join(CACHE_DIR, "apod.gif")
TMP_LOG = join(CACHE_DIR, "apod_debug.log")
TMP_JSON = join(CACHE_DIR, "apod_response.json")
DEFAULT_IMAGE = join(plugin_path, "res/icons/default_apod_image.jpg")
api_key_file = '/etc/apod_api_key'
api_key_file2 = '/etc/enigma2/apod_api_key',
today = date.today()
logger = logging.getLogger(title_plug)


# === Logging initialization ===
def init_logging():
    """
    Initializes logging for the APOD plugin.
    Logs are written to /tmp/apod_cache/apod_debug.log
    """
    handler = logging.FileHandler(TMP_LOG, mode='w', encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.info("=== APOD DEBUG START ===")


init_logging()

# === Config initialization ===
config.plugins.apod = ConfigSubsection()
config.plugins.apod.api_key = ConfigText(default="DEMO_KEY", fixed_size=False)
config.plugins.apod.count = ConfigSelection(
    default="50",
    choices=[(str(x), str(x)) for x in range(50, 1050, 50)]
)
config.plugins.apod.sort_order = ConfigSelection(
    default="Descending",
    choices=[
        ("Default", "Default"),
        ("Ascending", "Ascending"),
        ("Descending", "Descending")
    ]
)

try:
    config.plugins.apod.api_key.load()
except Exception as e:
    logger.exception("Failed to load API key from config: " + str(e))


"""
APOD - Astronomy Picture of the Day Plugin
Security and Download Improvements
"""


class SecurityError(Exception):
    """Exception raised for security-related errors"""
    pass

class DownloadError(Exception):
    """Exception raised for download-related errors"""
    pass

class APIError(Exception):
    """Exception raised for API-related errors"""
    pass


class SecurityManager:
    @staticmethod
    def validate_url(url):
        """Validate URL to prevent SSRF attacks"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['http', 'https']:
                return False

            # Allow only NASA domains and known CDNs
            allowed_domains = [
                'apod.nasa.gov',
                'api.nasa.gov',
                'www.nasa.gov',
                'images-assets.nasa.gov',
                'youtube.com',
                'youtu.be'
            ]

            domain = parsed.netloc.lower()
            if not any(allowed in domain for allowed in allowed_domains):
                logger.warning(f"Blocked unauthorized domain: {domain}")
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filenames to prevent path traversal"""
        from re import sub
        # Remove path components and special characters
        filename = sub(r'[^\w\-_.]', '_', filename)
        filename = filename.replace('..', '_')
        return filename[:255]

    @staticmethod
    def verify_file_integrity(file_path, expected_size=None):
        """Verify downloaded file integrity"""
        try:
            if not exists(file_path):
                return False

            file_size = getsize(file_path)
            if expected_size and abs(file_size - expected_size) > 1024:  # 1KB tolerance
                logger.warning("File size mismatch: " + str(file_size) + " vs " + str(expected_size))
                return False

            # Basic file type verification for images
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                with open(file_path, 'rb') as f:
                    header = f.read(12)

                    # Check for valid image headers
                    if header.startswith(b'\xff\xd8\xff'):  # JPEG
                        return True
                    elif header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                        return True
                    elif header.startswith(b'GIF8'):  # GIF
                        return True
                    else:
                        logger.warning("Invalid image file header")
                        return False

            return True

        except Exception as e:
            logger.error("File integrity check failed: " + str(e))
            return False


# === Apikey initialization ===
class APIKeyManager:
    @staticmethod
    def is_valid_api_key(key):
        """Check if API key is valid format"""
        if not key or key == "DEMO_KEY":
            return False
        clean_key = key.strip()
        return len(clean_key) == 40

    @staticmethod
    def load_apikey_from_file():
        possible_paths = [
            api_key_file,
            api_key_file2,
            join(plugin_path, 'apod_api_key'),
        ]

        for key_file in possible_paths:
            try:
                if exists(key_file):
                    with open(key_file, 'r') as f:
                        key = f.read().strip()
                        logger.info("Found API key file at: {}".format(key_file))
                        logger.info("Key length: {}".format(len(key)))

                        if APIKeyManager.is_valid_api_key(key):
                            config.plugins.apod.api_key.value = key
                            config.plugins.apod.api_key.save()
                            logger.info("Valid API key loaded successfully")
                            return True
                        else:
                            logger.warning("Invalid API key format")
            except Exception as e:
                logger.error("Error reading API key file: {}".format(e))

        return False


class SecureAPIClient:
    def __init__(self):
        self.session = requests.Session()
        # Configure secure TLS settings
        self.session.verify = True  # Enable certificate verification
        self.timeout = 15

    def safe_api_request(self, url, params=None):
        """Make API request with security measures"""
        if not SecurityManager.validate_url(url):
            raise SecurityError("Invalid URL")

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'APOD-Plugin/1.6',
                    'Accept': 'application/json'
                }
            )

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code}")
                raise APIError(f"API request failed with status code: {response.status_code}")

            # Validate JSON response
            data = response.json()
            if not isinstance(data, (list, dict)):
                raise APIError("Invalid API response format")

            return data

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error: {e}")
            raise SecurityError(f"SSL verification failed: {e}")
        except requests.exceptions.Timeout:
            logger.error("API request timeout")
            raise DownloadError("Request timeout")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            raise DownloadError("Connection failed")
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise APIError(f"Invalid API response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise APIError(f"Unexpected error during API request: {e}")


class SecureCacheManager:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.max_cache_size = 100 * 1024 * 1024  # 100MB
        self.cleanup_interval = 24 * 60 * 60  # 24 hours

    def secure_cache_path(self, filename):
        """Ensure cached files stay within cache directory"""
        safe_name = SecurityManager.sanitize_filename(filename)
        full_path = join(self.cache_dir, safe_name)

        # Prevent directory traversal
        if not full_path.startswith(self.cache_dir):
            raise SecurityError("Invalid cache path")

        return full_path

    def cleanup_old_files(self):
        """Remove old files while respecting cache limits"""
        try:
            files = []
            total_size = 0

            for f in listdir(self.cache_dir):
                if f in ['apod_debug.log', 'apod_response.json']:
                    continue  # Keep log files

                path = self.secure_cache_path(f)
                if exists(path):
                    mtime = getmtime(path)
                    size = getsize(path)
                    files.append((path, mtime, size))
                    total_size += size

            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[1])

            # Remove files until under limit
            while total_size > self.max_cache_size and files:
                oldest_path, _, size = files.pop(0)
                try:
                    remove(oldest_path)
                    total_size -= size
                    logger.info("Cleaned cache file: " + basename(oldest_path))
                except Exception as e:
                    logger.error("Failed to remove " + str(oldest_path) + ": " + str(e))

        except Exception as e:
            logger.error("Cache cleanup failed: " + str(e))

    def clear_sensitive_data(self):
        """Clear potentially sensitive data"""
        sensitive_patterns = ['apod_api_key', 'user_data']
        for f in listdir(self.cache_dir):
            if any(pattern in f for pattern in sensitive_patterns):
                try:
                    remove(join(self.cache_dir, f))
                except:
                    pass


class AdvancedDownloadManager:
    def __init__(self):
        self.concurrent_downloads = 0
        self.max_concurrent = 2
        self.download_queue = []
        self.active_downloads = {}

    def safe_download(self, url, local_path, callback, errback):
        """Download with comprehensive safety checks"""
        if not SecurityManager.validate_url(url):
            errback(Exception("URL validation failed"))
            return

        safe_path = join(CACHE_DIR, SecurityManager.sanitize_filename(basename(local_path)))

        if exists(safe_path):
            callback(safe_path)
            return

        if self.concurrent_downloads >= self.max_concurrent:
            self.download_queue.append((url, safe_path, callback, errback))
            return

        self.concurrent_downloads += 1
        self.active_downloads[url] = safe_path

        def on_success(result):
            self.concurrent_downloads -= 1
            if SecurityManager.verify_file_integrity(safe_path):
                callback(safe_path)
            else:
                # Remove corrupted file
                try:
                    remove(safe_path)
                except:
                    pass
                errback(Exception("File integrity check failed"))
            self.process_queue()

        def on_failure(failure):
            self.concurrent_downloads -= 1
            logger.error(f"Download failed: {failure}")
            errback(failure)
            self.process_queue()

        downloadPage(url.encode('utf-8'), safe_path, timeout=30
                     ).addCallbacks(on_success, on_failure)

    def process_queue(self):
        """Process queued downloads"""
        while self.download_queue and self.concurrent_downloads < self.max_concurrent:
            url, path, callback, errback = self.download_queue.pop(0)
            self.safe_download(url, path, callback, errback)

    def cancel_all_downloads(self):
        """Cancel all active and queued downloads"""
        self.download_queue = []
        # Note: Cannot cancel active twisted downloads easily
        # But we can mark them for cleanup
        self.concurrent_downloads = 0


class APODConfigScreen(ConfigListScreen, Screen):
    skin = """
        <screen name="APODConfigScreen" position="center,center" size="1280,720" title="APOD Plugin Settings" flags="wfNoBorder">
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/apod/res/icons/back.png" position="0,0" size="1280,720" alphatest="blend" zPosition="-1" />
            <widget name="config" position="50,100" size="1180,500" scrollbarMode="showOnDemand" />
            <widget name="key_green" position="250,620" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#008000" />
            <widget name="key_red" position="700,620" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#FF0000" />
            <widget name="title" position="50,40" size="1180,50" font="Regular;32" valign="center" halign="center" backgroundColor="#2a70a4" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)

        self.setTitle(_("APOD Plugin Settings"))
        self["title"] = Label(_("APOD Plugin Settings"))
        self["key_green"] = Label(_("Save"))
        self["key_red"] = Label(_("Cancel"))

        self.list = [
            getConfigListEntry(_("NASA API Key:"), config.plugins.apod.api_key),
            getConfigListEntry(_("Number of APODs to fetch:"), config.plugins.apod.count),
            getConfigListEntry(_("Sort order:"), config.plugins.apod.sort_order)
        ]

        ConfigListScreen.__init__(self, self.list)

        self["actions"] = HelpableActionMap(
            self, "ApodActions",
            {
                "ok": self.keySave,
                "cancel": self.keyCancel,
                "green": self.keySave,
                "red": self.keyCancel
            }, -1)

    def keySave(self):
        """Save configuration to both Enigma2 config and API key file"""
        try:
            api_key = config.plugins.apod.api_key.value
            if api_key and len(api_key) == 40 and api_key != "DEMO_KEY":
                with open(api_key_file, 'w') as f:
                    f.write(api_key)
                logger.info("API key saved to file")
        except Exception as e:
            logger.exception("Failed to save API key to file: {}".format(e))

        for x in self["config"].list:
            x[1].save()

        self.close(True)

    def keyCancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)


class SplashScreen(Screen):

    if screen_width == 1920:
        skin = """
            <screen name="SplashScreen" position="center,center" size="1920,1080" flags="wfNoBorder">
                <widget name="image" position="0,0" size="1920,1080" zPosition="1" alphatest="off" scale="1"/>
                <widget name="text" position="100,900" size="1720,100"
                    font="Regular;40" valign="center" halign="center" zPosition="2"/>
            </screen>"""
    else:
        skin = """
            <screen name="SplashScreen" position="center,center" size="1280,720" flags="wfNoBorder">
                <widget name="image" position="0,0" size="1280,620" zPosition="1" alphatest="off" scale="1" />
                <widget name="text" position="4,618" size="1274,100" font="Regular;40" valign="center" halign="center" zPosition="2" />
            </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["image"] = Pixmap()
        self["text"] = Label(_("Loading Astronomy Picture of the Day..."))
        self["actions"] = HelpableActionMap(
            self, "ApodActions",
            {
                "ok": self.show_list,
                "cancel": self.close
            }, -1
        )
        self.onLayoutFinish.append(self.start_loading)

    def start_loading(self):
        """
        Kick off a background thread to load today's APOD.
        Validates API key before proceeding.
        """
        api_key = config.plugins.apod.api_key.value
        if not api_key or api_key == "DEMO_KEY":
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Invalid API Key! Please configure a valid NASA API key."),
                MessageBox.TYPE_ERROR
            )
            return

        threads.deferToThread(self.load_apod).addCallback(self.show_image)

    def load_apod(self):
        try:
            api_key = config.plugins.apod.api_key.value
            url = "https://api.nasa.gov/planetary/apod?api_key={}".format(api_key)
            response = requests.get(url, timeout=10)
            data = response.json()

            logger.info("APOD API response: {}".format(data.get("title", "No title")))

            if data.get("media_type") != "image":
                raise ValueError("Today's APOD is not an image")

            img_url = data.get("url")  # Non usare hdurl che è TIFF!
            logger.info("Image URL: {}".format(img_url))

            # Download image
            img_response = requests.get(img_url, stream=True, timeout=15)
            img_response.raise_for_status()

            # Save with correct extension from URL
            parsed_url = urlparse(img_url)
            file_ext = splitext(parsed_url.path)[1].lower()

            if file_ext in ['.jpg', '.jpeg']:
                temp_path = TMP_IMG_JPG
            elif file_ext == '.png':
                temp_path = TMP_IMG_PNG
            elif file_ext == '.gif':
                temp_path = TMP_IMG_GIF
            else:
                temp_path = TMP_IMG_JPG  # default

            logger.info("Saving to: {}".format(temp_path))

            with open(temp_path, "wb") as f:
                copyfileobj(img_response.raw, f)

            logger.info("File saved, size: {} bytes".format(getsize(temp_path)))
            return data

        except Exception as e:
            logger.exception("Error loading APOD: {}".format(e))
            return None

    def show_image(self, data):
        if data is None:
            self["text"].setText(_("Failed to load APOD"))
            reactor.callLater(3, self.show_list)
            return

        self["text"].setText(data.get("title", ""))

        # List all files in the debug cache
        try:
            cache_files = listdir(CACHE_DIR)
            logger.info("Files in cache: {}".format(cache_files))
        except:
            pass

        image_path = None
        for path in [TMP_IMG_JPG, TMP_IMG_PNG, TMP_IMG_GIF]:
            if fileExists(path):
                image_path = path
                logger.info("Using image: {}".format(path))

                size = getsize(path)
                logger.info("File size: {} bytes".format(size))
                break

        if image_path:
            try:
                success = self["image"].instance.setPixmapFromFile(image_path)
                logger.info("setPixmapFromFile result: {}".format(success))

                if not success:
                    pixmap = LoadPixmap(image_path)
                    if pixmap:
                        self["image"].instance.setPixmap(pixmap)
                        logger.info("LoadPixmap successful")
                    else:
                        logger.error("Both methods failed")

            except Exception as e:
                logger.exception("Display error: {}".format(e))

        reactor.callLater(3, self.show_list)

    def _download_and_show(self, url):
        """
        Download a single image and display it immediately.
        """
        try:
            logger.info("Downloading splash fallback from {}".format(url))
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(TMP_IMG_JPG, "wb") as f:
                    f.write(r.content)
                self["image"].instance.setPixmapFromFile(TMP_IMG_JPG)
            else:
                self["text"].setText(_("Failed to fetch image: HTTP {}").format(r.status_code))
        except Exception as e:
            logger.exception("Error downloading splash image {}".format(e))
            self["text"].setText(_("Error downloading image: {}").format(str(e)))

    def show_list(self):
        """Open the ArchiveScreen and close this splash."""
        self.session.openWithCallback(self.close, ArchiveScreen)


class ArchiveScreen(Screen):
    skin = """
    <screen name="ArchiveScreen" position="center,center" size="1280,720" flags="wfNoBorder">
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/apod/res/icons/back.png" position="0,0" size="1280,720" alphatest="blend" zPosition="-3" cornerRadius="30" />
        <ePixmap position="0,0" size="1280,720" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/apod/res/icons/backgtr.png" alphatest="blend" zPosition="-2" cornerRadius="30" />
        <widget source="list" render="Listbox" position="6,59" size="1099,592" transparent="1" itemHeight="60" enableWrapAround="1" scrollbarMode="showNever">
            <convert type="TemplatedMultiContent">
                {
                    "template": [
                        MultiContentEntryPixmapAlphaBlend(
                            pos=(10, 5),
                            size=(50, 50),
                            png=0
                        ),
                        MultiContentEntryText(
                            pos=(70, 5),
                            size=(1100, 25),
                            font=0,
                            flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                            text=1
                        ),
                        MultiContentEntryText(
                            pos=(70, 30),
                            size=(1100, 25),
                            font=1,
                            flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                            text=2
                        )
                    ],
                    "fonts": [gFont("Regular", 24), gFont("Regular", 22)],
                    "itemHeight": 60
                }
            </convert>
        </widget>
        <widget name="title" position="5,5" size="1280,50" font="Regular; 32" transparent="1" zPosition="3" halign="center" />
        <widget name="status" position="5,657" size="1203,50" font="Regular;28" halign="center" />
        <eLabel name="" position="1155,109" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="MENU" />
        <eLabel name="" position="1155,197" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="OK" />
        <eLabel name="" position="1158,290" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="INFO" />
        <eLabel name="" position="1160,385" size="75,75" backgroundColor="#2a70a4" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="SEARCH" />
        <eLabel name="" position="1162,487" size="75,75" backgroundColor="#9f1313" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="EXIT" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = List([], enableWrapAround=True)
        self["status"] = Label(_("Loading..."))
        self["title"] = Label(title_plug)
        self.search_active = False
        self.shown = False
        self.raw_data = []
        self.icons = {
            "image": self.load_pixmap("icon_image.png"),
            "video": self.load_pixmap("icon_video.png"),
            "gif": self.load_pixmap("icon_gif.png")
        }

        self["actions"] = HelpableActionMap(
            self, "ApodActions",
            {
                "ok": self.show_details,
                "green": self.show_details,
                "menu": self.open_config,
                "cancel": self.closeApod,
                "red": self.closeApod,
                "blue": self.search_apod,
                "info": self.show_info
            }, -1)

        self.onLayoutFinish.append(self.start_loading)

    def load_pixmap(self, filename):
        """
        Load an icon from the plugin's resources.
        If not found, return a default 'unknown' icon.
        """
        try:
            path = join(plugin_path, "res", "icons", filename)
            if exists(path):
                pixmap = LoadPixmap(path)
                if pixmap:
                    logger.info("Loaded icon: {}".format(filename))
                    return pixmap
                else:
                    logger.warning("Failed to load pixmap: {}".format(filename))

            # Fallback
            fallback = join(plugin_path, "res", "icons", "icon_unknown.png")
            return LoadPixmap(fallback) if exists(fallback) else None

        except Exception as e:
            logger.error("Error loading pixmap {}: {}".format(filename, e))
            return None

    def start_loading(self):
        """
        Start fetching data - clear cache first for fresh data
        """
        logger.info("=== ARCHIVE SCREEN - CLEARING CACHE ===")
        logger.info("=== TESTING API KEY ===")
        try:
            if exists(TMP_JSON):
                remove(TMP_JSON)
                logger.info("Cleared old cache file")
        except:
            pass

        self["status"].setText(_("Loading fresh APOD data..."))
        threads.deferToThread(self.fetch_data).addCallbacks(
            self.on_data_fetched,
            self.on_data_error
        )

    def fetch_data(self):
        """Fetch fresh APOD entries from NASA API"""
        try:
            count = config.plugins.apod.count.value
            api_key = config.plugins.apod.api_key.value

            logger.info("Fetching fresh data - Count: {}, API Key: {}".format(count, api_key[:8] + "..." if api_key else "None"))

            if not APIKeyManager.is_valid_api_key(api_key):
                logger.error("Invalid API key")
                return []

            url = "https://api.nasa.gov/planetary/apod"
            params = {'api_key': api_key, 'count': count}

            logger.info("Making fresh API request...")
            response = requests.get(url, params=params, timeout=30)
            logger.info("Response status: {}".format(response.status_code))

            if response.status_code == 200:
                data = response.json()
                logger.info("Success! Received {} fresh entries".format(len(data) if data else 0))

                if data:
                    first = data[0]
                    logger.info("First entry date: {}, title: {}".format(
                        first.get('date', 'No date'),
                        first.get('title', 'No title')
                    ))

                try:
                    with open(TMP_JSON, 'w') as f:
                        json_dump(data, f)
                    logger.info("Fresh data saved to cache")
                except Exception as e:
                    logger.error("Cache save failed: {}".format(e))

                return data
            else:
                logger.error("API error {}: {}".format(response.status_code, response.text[:200]))
                return []

        except Exception as e:
            logger.exception("Fetch data exception: {}".format(e))
            return []

    def on_data_fetched(self, data):
        """
        Called once fresh data is fetched.
        """
        logger.info("=== FRESH DATA FETCHED ===")
        logger.info("Data length: {}".format(len(data) if data else 0))

        if not data:
            logger.warning("No fresh data received")
            self["status"].setText(_("No data available. Check API key."))
            self["list"].setList([])
            return

        self.raw_data = data
        self.search_active = False
        self.build_list(data)

    def on_data_error(self, failure):
        """Handle errors in data fetching"""
        logger.error("=== DATA ERROR ===")
        logger.error("Error: {}".format(failure))
        self["status"].setText(_("Error loading data"))
        # Prova a caricare dalla cache
        cached_data = self.load_cached_data()
        self.on_data_fetched(cached_data)

    def load_cached_data(self):
        """Load data from cache if present"""
        try:
            if exists(TMP_JSON):
                with open(TMP_JSON, 'r') as f:
                    data = json_load(f)
                logger.info("Loaded {} entries from cache".format(len(data)))
                return data
            return []
        except Exception as e:
            logger.error("Failed to load cache: {}".format(e))
            return []

    def build_list(self, data):
        """Build list entries from fetched APOD data"""
        if not data:
            self["status"].setText(_("Error loading data. Try later."))
            logger.warning("No data to build list")
            return

        sort_order = config.plugins.apod.sort_order.value
        logger.info("Building list with {} entries, sort order: {}".format(len(data), sort_order))

        try:
            if sort_order == "Ascending":
                data.sort(key=lambda x: x.get("date", ""))
            elif sort_order == "Descending":
                data.sort(key=lambda x: x.get("date", ""), reverse=True)

            list_items = []
            for item in data:
                try:
                    media_type = item.get("media_type", "image")
                    url = item.get("url", "")

                    if url.lower().endswith(".gif"):
                        icon_type = "gif"
                    elif media_type == "video":
                        icon_type = "video"
                    else:
                        icon_type = "image"

                    list_items.append((
                        self.icons.get(icon_type),      # Icon
                        item.get("date", "N/A"),        # Date
                        item.get("title", "Untitled"),  # Title
                        url,                            # Image or video URL
                        item.get("explanation", ""),    # Description
                        media_type                      # Media type
                    ))
                except Exception as e:
                    logger.warning("Skipped invalid APOD entry: {}".format(e))
                    continue

            logger.info("Built list with {} entries".format(len(list_items)))
            self["list"].setList(list_items)
            self["status"].setText(_("Found {} entries").format(len(list_items)))

        except Exception as e:
            logger.error("Build list failed: {}".format(e))
            self["status"].setText(_("Error building list"))

    def show_details(self):
        """
        Opens the DetailScreen with the currently selected APOD entry.
        """
        selected_index = self["list"].getIndex()
        if selected_index < len(self.raw_data):
            entry = self.raw_data[selected_index]
            self.session.open(DetailScreen, entry)

    def show_info(self):
        """
        Show a message box with the title and explanation of the selected APOD entry.
        """
        idx = self["list"].getIndex()
        if 0 <= idx < len(self.raw_data):
            entry = self.raw_data[idx]
            title = entry.get("title", "No Title")
            explanation = entry.get("explanation", "No Description")
            self.session.open(MessageBox, f"Title: {title}\n\nExplanation:\n{explanation}", MessageBox.TYPE_INFO)

    def search_apod(self):
        self.session.openWithCallback(
            self.on_search_entered,
            VirtualKeyBoard,
            title=_("Search..."),
            text=""
        )

    def on_search_entered(self, result):
        if not result:
            return
        term = result.lower()
        self.filtered_data = [e for e in self.raw_data if term in e.get("title", "").lower()]
        self.search_active = True
        self.build_list(self.filtered_data)
        self["status"].setText(_(f"Search results: {len(self.filtered_data)}"))

    def open_config(self):
        """
        Opens the plugin's configuration screen.
        When the user closes it, reload the APOD list with the new settings.
        """
        self.session.openWithCallback(
            self._on_config_closed,
            APODConfigScreen
        )

    def _on_config_closed(self, result):
        """
        Called when APODConfigScreen closes.
        'result' è True se l'utente ha premuto OK, False su Cancel.
        Se OK, rilanciamo il caricamento.
        """
        if result:
            logger.info("Configuration changed — reloading APOD list")
            self.start_loading()

    def closeApod(self):
        """
        Performs cleanup before closing the screen.
        """
        if self.search_active:
            self.search_active = False
            self.build_list(self.raw_data)
            self["status"].setText(_("Found " + str(len(self.raw_data)) + " entries"))
        else:
            self.clean_cache()
            self.close()

    def clean_cache(self):
        """Remove temporary cache directory if it exists."""
        try:
            for f in listdir(CACHE_DIR):
                if f.startswith("apod_vid_") or f.startswith("apod_aud_"):
                    remove(join(CACHE_DIR, f))
            logger.info("Cleaned media cache")
        except Exception as e:
            logger.exception(f"Cache cleanup error: {e}")


class DetailScreen(Screen):

    if screen_width == 1920:
        skin = """
        <screen name="DetailScreen" position="center,center" size="1600,900" flags="wfNoBorder">
            <widget name="image" position="75,72" size="1459,586" alphatest="off" scale="1" cornerRadius="90" zPosition="3" />
            <widget name="date" position="1160,5" size="350,60" font="Regular;26" halign="right" valign="center" zPosition="3" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
            <widget name="title" position="80,5" size="1075,60" font="Regular;32" halign="center" valign="center" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
            <widget name="description" position="12,662" size="1569,237" font="Regular;26" transparent="1" zPosition="3" />
            <eLabel name="" position="1520,0" size="70,70" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="3" text="INFO" />
        </screen>"""
    else:
        skin = """
        <screen name="DetailScreen" position="center,center" size="1280,720" flags="wfNoBorder">
            <widget name="image" position="1,74" size="1280,420" alphatest="off" scale="1" cornerRadius="90" zPosition="3" />
            <widget name="date" position="835,5" size="350,60" font="Regular;26" halign="right" valign="center" zPosition="3" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
            <widget name="title" position="5,5" size="830,60" font="Regular;32" halign="center" valign="center" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
            <widget name="description" position="0,498" size="1282,220" font="Regular;26" transparent="1" zPosition="3" />
            <eLabel name="" position="1199,5" size="70,70" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="3" text="INFO" />
        </screen>"""

    def __init__(self, session, data):
        Screen.__init__(self, session)
        self.data = data
        self.active = True
        self["image"] = Pixmap()
        self["title"] = Label(self.data.get("title", ""))
        self["date"] = Label(self.data.get("date", ""))
        self["description"] = Label("")

        self["actions"] = HelpableActionMap(
            self, "ApodActions",
            {
                "ok": self.on_ok,
                "cancel": self.close,
                "info": self.show_info
            }, -1
        )

        self.onLayoutFinish.append(self.load_media)

    def load_media(self):
        """Branch: image or video?"""
        if not self.active:
            return

        mt = self.data.get("media_type")
        if mt == "image":
            self.load_image()
        elif mt == "video":
            self["description"].setText(_("Press OK to play video"))
        elif mt == "gif":
            url = self.data.get("hdurl") or self.data.get("url")
            self.show_animated_gif(url)
        else:
            self["description"].setText(self.data.get("explanation", ""))

    def load_image(self, url=None, force=False):
        """
        Download and display the image
        """
        self["description"].setText(_("Loading image..."))
        if not url:
            url = self.data.get("hdurl") or self.data.get("url")
            if not url:
                self["description"].setText(_("No image URL available"))
                return

        if not force:
            parsed_url = urlparse(url)
            file_ext = splitext(parsed_url.path)[1].lower() or ".jpg"
            filename = "{}{}".format(self.data['date'], file_ext)
            local_path = join(CACHE_DIR, filename)

            if exists(local_path):
                self.update_image(local_path)
                return

        self.download_image(url, local_path if not force else None)

    def download_image(self, url, local_path=None):
        """Download image using downloadPage"""
        try:
            if not local_path:
                parsed_url = urlparse(url)
                file_ext = splitext(parsed_url.path)[1].lower() or ".jpg"
                filename = "{}{}".format(self.data['date'], file_ext)
                local_path = join(CACHE_DIR, filename)
            logger.info("Downloading image: {}".format(url))
            downloadPage(
                url.encode('utf-8'),
                local_path
            ).addCallbacks(
                lambda result: self.update_image(local_path),
                lambda failure: self.handle_download_error(failure, url)
            )
        except Exception as e:
            logger.error("Download error: {}".format(e))
            self.handle_download_error(e, url)

    def update_image(self, path):
        """
        Show the image from the given path, then set the explanation text.
        """
        if exists(path):
            try:
                self["image"].instance.setPixmapFromFile(path)
                self["description"].setText(self.data.get("explanation", ""))
                logger.info("Image displayed: {}".format(path))
            except Exception as e:
                logger.error("Failed to display image: {}".format(e))
                self["description"].setText(_("Error displaying image"))
        else:
            logger.warning("Image file not found: {}".format(path))
            self["description"].setText(_("Image not available"))

    def handle_download_error(self, error, url):
        """Handle download errors"""
        logger.error("Download failed for {}: {}".format(url, error))
        self["description"].setText(_("Failed to download image"))

    def on_ok(self):
        """OK: either play video/gif or reload image."""
        if not self.active:
            return

        mt = self.data.get("media_type")
        if mt == "video":
            logger.info("for video")
            self.play_video()

        elif mt == "gif":
            url = self.data.get("hdurl") or self.data.get("url")
            logger.info("for gif " + str(self.data.get("date")) + ": " + str(url))
            self.show_animated_gif(url)

        elif mt == "image":
            lowres_url = self.data.get("url")  # low resolution URL
            logger.info("for image: " + str(lowres_url))
            self.load_image(lowres_url, force=True)

        else:
            self.close()

    def play_video(self):
        """
        Download & merge YouTube audio/video, then launch MoviePlayer.
        """
        url = self.data.get("url", "")
        logger.info("Playing video: {}".format(url))

        # extract ID YouTube
        m = search(r"(?:v=|youtu\.be/|embed/)([\w-]+)", url)
        if not m:
            return self.session.open(MessageBox, _("Unsupported video URL"), MessageBox.TYPE_INFO)
        vid = m.group(1)

        logger.debug(f"play_video vid video():  {vid}")

        try:
            try:
                from youtube_dl import YoutubeDL
            except ImportError:
                self.session.open(MessageBox, 'Please install "YoutubeDL" plugin!', MessageBox.TYPE_ERROR)
                return

            try:
                yt_url = 'https://www.youtube.com/watch?v={}'.format(vid)
                stream = eServiceReference(4097, 0, yt_url)
                ydl_opts = {'format': 'best'}
                ydl = YoutubeDL(ydl_opts)
                ydl.add_default_info_extractors()
                result = ydl.extract_info(yt_url, download=False)
                if result and 'url' in result:
                    video_url = result['url']
                    print("Here in Test url = %s" % video_url)

                stream = eServiceReference(4097, 0, video_url)
                logger.debug(f"Extracted video URL: {stream}")
                stream.setName(self.data.get('title', 'APOD Video'))
                self.session.open(MoviePlayer, stream)

            except Exception as e:
                logger.error("Video playback error: {}".format(e))
                self.session.open(MessageBox, _("Video playback failed"), MessageBox.TYPE_INFO)
        except Exception as e:
            logger.exception("Error in play_video(): %s", e)
            self.session.open(MessageBox, _("Video playback failed"), MessageBox.TYPE_INFO)

    def show_animated_gif(self, url):
        try:
            from enigma import ePicLoad
            self.picload = ePicLoad()
            self.picload.setPara(
                (
                    self["image"].instance.size().width(),
                    self["image"].instance.size().height(),
                    1, 1, 0, 0, '#00000000'
                )
            )

            self.picload.startDecode(url)
            self.gif_timer = eTimer()
            self.gif_timer.callback.append(self.check_gif_status)
            self.gif_timer.start(100)
        except Exception as e:
            logger.error("GIF error: " + str(e))

    def check_gif_status(self):
        if self.picload.getData() is None:
            return
        self["image"].instance.setPixmap(self.picload.getData())

    def _cleanup_video(self, *args):
        """Delete temporary files after closing MoviePlayer."""
        for fn in listdir(CACHE_DIR):
            if fn.startswith(("apod_vid_", "apod_aud_", "apod_out_")):
                try:
                    remove(join(CACHE_DIR, fn))
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {fn}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error removing file {fn}: {e}")

    def show_info(self):
        """Show detailed info"""
        title = self.data.get("title", "No Title")
        explanation = self.data.get("explanation", "No Description")
        msg = "{}\n\n{}".format(title, explanation)
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def handle_error(self, failure):
        """
        Called if downloadPage fails.
        Logs the error and shows a fallback message.
        """
        logger.error(f"Error downloading image: {failure}")
        self["description"].setText(_("Failed to load image."))

    def close(self):
        self.active = False
        if hasattr(self, 'picload'):
            self.picload = None
        Screen.close(self)


def debug_api_key_status():
    """Log dello stato della API key per debug"""
    api_key = config.plugins.apod.api_key.value
    logger.info("=== API KEY DEBUG ===")
    logger.info("API Key from config: {}".format(api_key))
    logger.info("API Key length: {}".format(len(api_key) if api_key else 0))
    logger.info("API Key is DEMO_KEY: {}".format(api_key == "DEMO_KEY"))
    logger.info("=== END DEBUG ===")


def check_api_key_locations():
    """Check all possible API key locations"""
    possible_paths = [
        api_key_file,
        api_key_file2,
        join(plugin_path, 'apod_api_key'),
        '/usr/lib/enigma2/python/Plugins/Extensions/apod/apod_api_key'
    ]

    logger.info("=== API KEY LOCATION CHECK ===")
    for path in possible_paths:
        exists_flag = "EXISTS" if exists(path) else "MISSING"
        logger.info("{} - {}".format(path, exists_flag))
    logger.info("=== END LOCATION CHECK ===")


def main(session, **kwargs):
    """Main entry point"""
    logger.info("=== APOD PLUGIN START ===")
    key_loaded = APIKeyManager.load_apikey_from_file()
    api_key = config.plugins.apod.api_key.value
    is_valid = APIKeyManager.is_valid_api_key(api_key)

    logger.info("Key loaded from file: {}".format(key_loaded))
    logger.info("Final API key: {}".format(api_key))
    logger.info("Final API key length: {}".format(len(api_key) if api_key else 0))
    logger.info("Is valid: {}".format(is_valid))

    if is_valid:
        logger.info("Opening SplashScreen")
        session.open(SplashScreen)
    else:
        logger.info("Opening APODConfigScreen")
        session.open(APODConfigScreen)


def plugins(**kwargs):
    return [PluginDescriptor(
        name="NASA APOD Viewer",
        description=_(title_plug),
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon='logo.png',
        fnc=main
    )]


Plugins = plugins

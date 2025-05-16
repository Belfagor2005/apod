# -*- coding: utf-8 -*-
from __future__ import print_function

"""
#########################################################
#                                                       #
#  APOD - Astronomy Picture of the Day Plugin           #
#  Version: 1.6                                         #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0                             #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#  Last Modified: "15:14 - 20250513"                    #
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
#                                                       #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""
__author__ = "Lululla"


# Standard library
from datetime import date
from os.path import join, exists, splitext
from os import makedirs, remove, listdir
from re import search
from json import dump as json_dump, load as json_load, loads as json_loads
from shutil import copyfileobj
import logging

# Third-party libraries
import requests
from twisted.internet import reactor, threads
from twisted.web.client import downloadPage
from Screens.VirtualKeyBoard import VirtualKeyBoard

# Enigma2 core
from enigma import eTimer, eServiceReference

# Enigma2 components
from Components.ActionMap import HelpableActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.config import (
	config,
	ConfigSelection,
	ConfigSubsection,
	ConfigText,
	getConfigListEntry
)

# Enigma2 screens
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer

# Enigma2 plugin
from Plugins.Plugin import PluginDescriptor

# Tools
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists

# Local project
from . import _


"""
---

### **How to Use the NASA API Key for the APOD Plugin** 🚀
#### **1. Obtain the NASA API Key** 🌌
To access the Astronomy Picture of the Day (APOD) data from NASA, you need a valid API key.

* Visit the NASA API registration page:
	https://api.nasa.gov/`

* After completing the registration, you will receive a unique API key that grants access to the data.
---

#### **2. Adding the API Key to Your System** 🔑
Once you have the API key, store it securely on your system.

##### **Method 1: Create a file for the API Key** 📂
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

#### **3. Restart the System to Apply Changes** 🔄
After saving the API key, restart the plugin or GUI so the key can be loaded correctly.

---

#### **4. Troubleshooting** ⚠️
* **Invalid API Key Error**: Check the contents of your key file and ensure the key is copied exactly as provided.
* **Permission Issues**: Ensure the key file has the correct permissions (`chmod 600`).
* **Missing File**: Make sure the key exists in one of the expected paths.
---
Once done, the plugin should be able to access NASA's APOD data and display the Astronomy Picture of the Day properly. ✨
---

"""


currversion = '1.6'
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
	logger.exception(f"Failed to load API key from config {e}")


# === Apikey initialization ===
def load_apikey_from_file():
	"""
	Attempts to load the NASA API key from /etc/apod_api_key.
	If valid (length = 40), sets it into the plugin config.
	"""
	try:
		with open(api_key_file, 'r') as f:
			key = f.read().strip()
			if len(key) == 40:
				config.plugins.apod.api_key.value = key
				config.plugins.apod.api_key.save()
				logger.info("API key successfully loaded from file")
				return True
	except Exception as e:
		logger.exception(f"Error reading API key from file {e}")
	return False


"""
def default_image():
	return {
		"title": "Default Image",
		"explanation": "This is a fallback image used in the case where there is a missing/corrupted asset on apod.nasa.gov.",
		"url": "https://api.nasa.gov/planetary/apod/static/default_apod_image.jpg",
		"hdurl": "https://api.nasa.gov/planetary/apod/static/default_apod_image.jpg",
		"media_type": "image",
	}
"""


class APODConfigScreen(ConfigListScreen, Screen):
	"""
	Configuration screen for the APOD plugin.
	Allows setting NASA API key and number of images to fetch.
	Triggered from the main screen via green button.
	"""

	skin = """
		<screen name="APODConfigScreen" position="center,center" size="1280,720" title="APOD Plugin Settings" flags="wfNoBorder">
			<widget name="config" position="50,100" size="1180,500" scrollbarMode="showOnDemand" />
			<widget name="save" position="250,620" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#008000" />
			<widget name="cancel" position="700,620" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#FF0000" />
			<widget name="title" position="50,40" size="1180,50" font="Regular;32" valign="center" halign="center" backgroundColor="#2a70a4,mint,lmsb,horizontal" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self.setTitle(_("APOD Plugin Settings"))
		self["title"] = Label(title_plug)
		self["key_green"] = Label(_("Save"))
		self["key_red"] = Label(_("Close"))
		self.list = [
			getConfigListEntry(_("NASA API Key:"), config.plugins.apod.api_key),
			getConfigListEntry(_("Number of APODs to fetch:"), config.plugins.apod.count),
			getConfigListEntry(_("Sort order:"), config.plugins.apod.sort_order)
		]
		ConfigListScreen.__init__(self, self.list)

		self["actions"] = HelpableActionMap(
			self, "ApodActions",
			{
				"ok": self.save,
				"cancel": self.cancel,
				"green": self.save
			}, -1)

	def save(self):
		try:
			with open(api_key_file, "w") as f:
				f.write(config.plugins.apod.api_key.value)
		except Exception as e:
			logger.exception(f"Failed to save API key to  {api_key_file} {e}")

		for x in self["config"].list:
			x[1].save()
		self.close(True)

	def cancel(self):
		self.close(False)


class SplashScreen(Screen):
	"""
	Splash screen that displays today's APOD image or a default fallback.
	After 5 seconds, it opens the ArchiveScreen.
	"""

	skin = """
		<screen name="SplashScreen" position="center,center" size="1920,1080" flags="wfNoBorder">
			<widget name="image" position="0,0" size="1920,1080" zPosition="1" alphatest="off" scale="1"/>
			<widget name="text" position="100,900" size="1720,100"
				font="Regular;40" valign="center" halign="center" zPosition="2"/>
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
			self.show_error(_("Invalid API Key! Please configure a valid NASA API key."))
			return
		threads.deferToThread(self.load_apod).addCallback(self.show_image)

	def load_apod(self):
		try:
			api_key = config.plugins.apod.api_key.value
			url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
			response = requests.get(url, timeout=10)
			data = response.json()

			if data.get("media_type") != "image":
				raise ValueError("Today's APOD is not an image")

			img_url = data.get("hdurl") or data.get("url")
			img_response = requests.get(img_url, stream=True, timeout=15)
			img_response.raise_for_status()

			with open(TMP_IMG_JPG, "wb") as f:
				copyfileobj(img_response.raw, f)

			return data

		except Exception as e:
			logger.exception(f"Error loading APOD: {e}")
			"""
			fb = default_image()
			try:
				# img_response = requests.get(fb["url"], timeout=10)
				# img_response.raise_for_status()
				with open(TMP_IMG_JPG, "wb") as f:
					# copyfileobj(img_response.raw, f)
					copyfileobj(DEFAULT_IMAGE, f)
			except Exception:
				logger.exception("Failed to download default APOD image")
			"""
			return DEFAULT_IMAGE  # fb

	def show_image(self, data):
		"""
		Display the cached image (JPG or PNG) or download on the fly.
		Then transition to ArchiveScreen after 5 seconds.
		"""
		if isinstance(data, str):
			self["text"].setText(_("Error: %s") % data)
			return

		self["text"].setText(data.get("title", ""))

		# Choose cached file if exists
		if fileExists(TMP_IMG_JPG):
			path = TMP_IMG_JPG
			self.typo = '.jpg'
		elif fileExists(TMP_IMG_PNG):
			path = TMP_IMG_PNG
			self.typo = '.png'
		elif fileExists(TMP_IMG_GIF):
			path = TMP_IMG_GIF
			self.typo = '.gif'
		else:
			# Fallback: download directly
			url = data.get("url", "")
			if url:
				self._download_and_show(url)
				reactor.callLater(5, self.show_list)
				return
			else:
				self["text"].setText(_("No image URL found."))
				return

		self["image"].instance.setPixmapFromFile(path)
		reactor.callLater(5, self.show_list)

	def _download_and_show(self, url):
		"""
		Download a single image (no cache) and display it immediately.
		"""
		try:
			logger.info(f"Downloading splash fallback from {url}")
			r = requests.get(url, timeout=10)
			if r.status_code == 200:
				with open(TMP_IMG_JPG, "wb") as f:
					f.write(r.content)
				self["image"].instance.setPixmapFromFile(TMP_IMG_JPG)
			else:
				self["text"].setText(_("Failed to fetch image: HTTP %d") % r.status_code)
		except Exception as e:
			logger.exception(f"Error downloading splash image {e}")
			self["text"].setText(_("Error downloading image: %s") % str(e))
			# self["text"].setText(_("This is a fallback image used in the case where there is a missing/corrupted asset on apod.nasa.gov."))

	def show_list(self):
		"""Open the ArchiveScreen and close this splash."""
		self.session.openWithCallback(self.close, ArchiveScreen)


class ArchiveScreen(Screen):
	skin = """
	<screen name="ArchiveScreen" position="center,center" size="1600,900" flags="wfNoBorder">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/apod/res/icons/back.png" position="0,0" size="1600,900" alphatest="blend" zPosition="-3" cornerRadius="30" />
		<ePixmap position="0,0" size="1600,900" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/apod/res/icons/backgtr.png" alphatest="blend" zPosition="-2" cornerRadius="30" />
		<widget source="list" render="Listbox" position="204,60" size="1200,740" transparent="1" itemHeight="60" enableWrapAround="1" scrollbarMode="showNever">
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
		<widget name="title" position="5,5" size="1600,50" font="Regular; 32" transparent="1" zPosition="3" halign="center" />
		<widget name="status" position="203,815" size="1203,50" font="Regular;28" halign="center" />
		<eLabel name="" position="1465,210" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="MENU" />
		<eLabel name="" position="1465,300" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="OK" />
		<eLabel name="" position="1465,390" size="75,75" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="INFO" />
		<eLabel name="" position="1465,480" size="75,75" backgroundColor="#2a70a4" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="SEARCH" />
		<eLabel name="" position="1465,570" size="75,75" backgroundColor="#9f1313" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="1" text="EXIT" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["list"] = List([])
		self["status"] = Label(_("Loading..."))
		self["title"] = Label(title_plug)
		self.search_active = False
		self.shown = False
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

		# self.onShow.append(self.start_loading)
		self.onLayoutFinish.append(self.start_loading)

	def load_pixmap(self, filename):
		"""
		Load an icon from the plugin's resources.
		If not found, return a default 'unknown' icon.
		"""
		try:
			path = join(plugin_path, "res", "icons", filename)
			if exists(path):
				return LoadPixmap(path)
			fallback = join(plugin_path, "res", "icons", "icon_unknown.png")
			return LoadPixmap(fallback)
		except Exception as e:
			print(f"[APOD] Failed to load pixmap '{filename}': {e}")
			return None

	def start_loading(self):
		"""
		Start fetching data from NASA API using a background thread.
		"""
		"""
		def _fetch_wrapper():
			try:
				data = self.fetch_data()
				self.raw_data = data
				if self.shown:
					self.on_data_fetched(data)
			except Exception as e:
				logger.error(f"Thread error: {str(e)}")
		threads.deferToThread(_fetch_wrapper)
		"""
		threads.deferToThread(self.fetch_data).addCallback(self.on_data_fetched)

	def on_data_fetched(self, data):
		"""
		Called once data is fetched. Stores raw JSON and populates list.
		"""
		# self.raw_data = data
		self.search_active = False
		self.build_list(data)

	def fetch_data(self):
		"""Fetch APOD entries from NASA API and save them locally as JSON."""
		try:
			count = config.plugins.apod.count.value
			api_key = config.plugins.apod.api_key.value
			url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&count={count}"
			logger.info(f"Requesting {count} APOD entries from {url}")

			# Create urllib3 Pool Manager
			import urllib3
			http = urllib3.PoolManager()
			video_request = http.request("GET", url)

			if video_request.status == 200:
				data = json_loads(video_request.data.decode('utf-8'))
				self.raw_data = data
				with open('/tmp/apod_cache/test.json', "w") as f:
					json_dump(data, f)
				return data
				"""
				# response = requests.get(url, timeout=20)
				# if response.status_code == 200:
					# data = response.json()
					# with open(TMP_JSON, "w") as f:
						# json_dump(data, f)
					# logger.info(f"Fetched {len(data)} APOD entries")
					# return data
				"""
			else:
				logger.error(f"NASA API error: {video_request.status_code}")
				return self.load_cached_data()  # Fallback al cache se disponibile
		except Exception as e:
			logger.exception(f"Failed to fetch data from NASA API{e}")
			return self.load_cached_data()  # Fallback al cache

	def load_cached_data(self):
		"""Load data from cache if present"""
		try:
			if exists(TMP_JSON):
				with open(TMP_JSON, "r") as f:
					return json_load(f)
			return []
		except Exception as e:
			logger.error(f"Failed to load cache: {e}")
			return []

	def build_list(self, data):
		"""Build list entries from fetched APOD data with optional sorting."""
		if not data:
			self["status"].setText(_("Error loading data. Try later."))
			return
		sort_order = config.plugins.apod.sort_order.value

		try:
			if sort_order == "Ascending":
				data.sort(key=lambda x: x.get("date", ""))
			elif sort_order == "Descending":
				data.sort(key=lambda x: x.get("date", ""), reverse=True)
			# "Default" keeps original order
			list_items = []
			for item in data:
				try:
					media_type = item.get("media_type", "image")
					url = item.get("url", "")

					if url.lower().endswith(".gif"):
						media_type = "gif"

					list_items.append((
						self.icons.get(item.get("media_type", "image")),  # Icon
						item.get("date", "N/A"),                          # Date
						item.get("title", "Untitled"),                    # Title
						item.get("url", ""),                              # Image or video URL
						item.get("explanation", ""),                      # Description
						# item.get("media_type", "image")                   # Media type
						media_type
					))
				except Exception as e:
					logger.warning(f"Skipped invalid APOD entry: {e}")
					continue

			logger.info(f"Built list with {len(list_items)} entries")
			self.search = False
			self["list"].setList(list_items)
			self["status"].setText(f"Found {len(list_items)} entries")
		except Exception as e:
			logger.error(f"Build list failed: {str(e)}")

	def show_details(self):
		"""
		Opens the DetailScreen with the currently selected APOD entry.
		"""
		idx = self["list"].getIndex()
		if 0 <= idx < len(self.raw_data):
			entry = self.raw_data[idx]
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
			self["status"].setText(_(f"Found {len(self.raw_data)} entries"))
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
	"""
	Detail screen for a single APOD entry.
	Downloads the high‑resolution image (if not cached),
	displays it, and shows title, date and explanation.
	"""

	skin = """
	<screen name="DetailScreen" position="center,center" size="1600,900" flags="wfNoBorder">
		<widget name="image" position="75,72" size="1459,586" alphatest="off" scale="1" cornerRadius="90" zPosition="3" />
		<widget name="date" position="1160,5" size="350,60" font="Regular;26" halign="right" valign="center" zPosition="3" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
		<widget name="title" position="80,5" size="1075,60" font="Regular;32" halign="center" valign="center" backgroundGradient="#2a70a4,mint,lmsb,horizontal" />
		<widget name="description" position="12,662" size="1569,237" font="Regular;26" transparent="1" zPosition="3" />
		<eLabel name="" position="1520,0" size="70,70" backgroundColor="#002a2a2a" halign="center" valign="center" transparent="0" cornerRadius="40" font="Regular; 17" zPosition="3" text="INFO" />
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
			# self["description"].setText(_("Press OK to play gif"))
		else:
			self["description"].setText(self.data.get("explanation", ""))

	def on_ok(self):
		"""OK: either play video/gif or reload image."""
		if not self.active:
			return

		mt = self.data.get("media_type")

		if mt == "video":
			logger.info("for video")
			self.play_video()
			return

		elif mt == "gif":
			url = self.data.get("hdurl") or self.data.get("url")
			logger.info(f"for gif {self.data['date']}: {url}")
			self.show_animated_gif(url)
			return

		elif mt == "image":
			lowres_url = self.data.get("url")  # URL a bassa risoluzione
			logger.info(f"for image: {lowres_url}")
			self.load_image(lowres_url, force=True)
			return

		else:
			self.close()

	def load_image(self, url=None, force=False):
		"""
		Download the image if not already cached, then call update_image().
		Displays a 'Wait please...' message until done.
		"""
		if not url:
			url = self.data.get("hdurl") or self.data.get("url")

		self["description"].setText(_("Wait please..."))
		if self.data.get("media_type") != "image":
			# No image to load for video or other media
			self["description"].setText(self.data.get("explanation", ""))
			return

		# Determine URL and extension
		url = self.data.get("hdurl") or self.data.get("url")
		ext = splitext(url)[1] or ".jpg"
		filename = f"{self.data['date']}{ext}"
		local_path = join(CACHE_DIR, filename)

		if force or not exists(local_path):
			logger.info(f"Downloading image for {self.data['date']}: {url}")
			downloadPage(
				url.encode(),
				local_path
			).addCallbacks(
				lambda _: self.update_image(local_path),
				self.handle_error
			)

		elif not exists(local_path):
			logger.info(f"Downloading image for {self.data['date']}: {url}")
			downloadPage(
				url.encode(),
				local_path
			).addCallbacks(
				lambda _: self.update_image(local_path),
				self.handle_error
			)

		else:
			logger.info(f"Using cached image: {local_path}")
			self.update_image(local_path)

	def update_image(self, path):
		"""
		Show the image from the given path, then set the explanation text.
		"""
		if exists(path):
			try:
				self["image"].instance.setPixmapFromFile(path)
				self["image"].show()
				logger.info(f"Image loaded: {path}")
			except Exception as e:
				logger.exception(f"Failed to display image: {e}")
		else:
			logger.warning(f"Image file missing after download: {path}")

		self["description"].setText(self.data.get("explanation", ""))

	def play_video(self):
		"""
		Download & merge YouTube audio/video, then launch MoviePlayer.
		"""
		url = self.data.get("url", "")
		logger.debug(f"play_video url video():  {url}")

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
				yt_url = f'https://www.youtube.com/watch?v={vid}'
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
				logger.error(f"Video playback error: {str(e)}", exc_info=True)
				self.session.open(MessageBox, _("Video playback failed"), MessageBox.TYPE_INFO)
		except Exception as e:
			logger.exception("Error in play_video(): %s", e)
			self.session.open(MessageBox, _("Video playback failed"), MessageBox.TYPE_INFO)

	def show_animated_gif(self, url):
		try:
			from enigma import ePicLoad
			self.picload = ePicLoad()
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
			logger.error(f"GIF error: {str(e)}")

	def check_gif_status(self):
		if self.picload.getData() is None:
			return
		self["image"].instance.setPixmap(self.picload.getData())

	def _cleanup_video(self, *args):
		"""Elimina file temporanei dopo la chiusura di MoviePlayer."""
		for fn in listdir(CACHE_DIR):
			if fn.startswith(("apod_vid_", "apod_aud_", "apod_out_")):
				try:
					remove(join(CACHE_DIR, fn))
				except:
					pass

	def show_info(self):
		"""
		INFO: apre un MessageBox con titolo   e spiegazione complete.
		"""
		title = self.data.get("title", "No Title")
		explanation = self.data.get("explanation", "No Description")
		msg = f"{title}\n\n{explanation}"
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


def main(session, **kwargs):
	if not load_apikey_from_file():
		logger.info("[APOD] API key not found, open configuration screen")
		session.open(APODConfigScreen)
	else:
		session.open(SplashScreen)


def Plugins(**kwargs):
	return [PluginDescriptor(
		name="NASA APOD Viewer",
		description=_(title_plug),
		where=PluginDescriptor.WHERE_PLUGINMENU,
		icon='logo.png',
		fnc=main
	)]

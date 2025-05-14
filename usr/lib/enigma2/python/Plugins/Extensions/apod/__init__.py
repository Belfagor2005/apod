#!/usr/bin/python
# -*- coding: utf-8 -*-

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext
import os


PluginLanguageDomain = 'apod'
PluginLanguagePath = 'Extensions/apod/res/locale'
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
isDreamOS = False
if os.path.exists("/usr/bin/apt-get"):
	isDreamOS = True


def localeInit():
	if isDreamOS:  # check if opendreambox image
		lang = language.getLanguage()[:2]  # getLanguage returns e.g. "fi_FI" for "language_country"
		os.environ["LANGUAGE"] = lang  # Enigma doesn't set this (or LC_ALL, LC_MESSAGES, LANG). gettext needs it!
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


if isDreamOS:
	def _(txt):
		return gettext.dgettext(PluginLanguageDomain, txt) if txt else ""
else:
	def _(txt):
		translated = gettext.dgettext(PluginLanguageDomain, txt)
		if translated:
			return translated
		else:
			print(("[%s] fallback to default translation for %s" % (PluginLanguageDomain, txt)))
			return gettext.gettext(txt)


localeInit()
language.addCallback(localeInit)

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

__author__ = "Lululla"
__email__ = "ekekaz@gmail.com"
__copyright__ = "Copyright (c) 2024 Lululla"
__license__ = "GPL-v2"
__version__ = "2.1"
DEBUG = True
SYSTEM_DIR = '/etc/enigma2/foreca'

PluginLanguageDomain = 'apod'
PluginLanguagePath = 'Extensions/apod/res/locale'
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


def localeInit():
    gettext.bindtextdomain(
        PluginLanguageDomain,
        resolveFilename(SCOPE_PLUGINS, PluginLanguagePath)
    )


def _(txt):
    translated = gettext.dgettext(PluginLanguageDomain, txt)
    if translated:
        return translated
    else:
        print(
            "[%s] fallback to default translation for %s" %
            (PluginLanguageDomain, txt))
        return gettext.gettext(txt)


localeInit()
language.addCallback(localeInit)

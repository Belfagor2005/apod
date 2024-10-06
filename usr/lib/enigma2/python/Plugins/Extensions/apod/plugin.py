#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
****************************************
*        coded by Lululla              *
*                                      *
*             01/09/2024               *
****************************************
Info http://t.me/tivustream
'''
from __future__ import print_function
from . import _, checkGZIP
from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import (MultiContentEntryText, MultiContentEntryPixmapAlphaTest)
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from enigma import (
    RT_VALIGN_CENTER,
    RT_HALIGN_LEFT,
    eListboxPythonMultiContent,
    eTimer,
    loadPNG,
    getDesktop,
    gFont,
    ePicLoad,
    # gPixmapPtr,
)
from twisted.web.client import getPage
import os
import ssl
import sys
import re
import codecs

PY3 = False


if sys.version_info[0] == 3:
    from urllib.request import urlopen
    PY3 = True
else:
    from urllib2 import urlopen
# print('Py3: ', PY3)


if sys.version_info >= (2, 7, 9):
    try:
        sslContext = ssl._create_unverified_context()
    except:
        sslContext = None

try:
    from twisted.internet import ssl
    from twisted.internet._sslverify import ClientTLSOptions
    sslverify = True
except:
    sslverify = False

if sslverify:
    class SNIFactory(ssl.ClientContextFactory):
        def __init__(self, hostname=None):
            self.hostname = hostname

        def getContext(self):
            ctx = self._contextFactory(self.method)
            if self.hostname:
                ClientTLSOptions(self.hostname, ctx)
            return ctx


def ssl_urlopen(url):
    if sslContext:
        return urlopen(url, context=sslContext)
    else:
        return urlopen(url)


global tmpimg, tmpImg

currversion = '1.5'
title_plug = '..:: Picture of The Day - Nasa %s ::..' % currversion
name_plug = 'Picture of The Day'
Credits = 'Info http://t.me/tivustream'
Maintener = 'Maintener @Lululla'
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
tmpImg = os.path.join(plugin_path, 'res/pics/vialattea.png')
tmpimg = os.path.join('/tmp', 'image.png')
screenwidth = getDesktop(0).size()
if screenwidth.width() == 2560:
    skin_path = plugin_path + '/res/skins/uhd/'
elif screenwidth.width() == 1920:
    skin_path = plugin_path + '/res/skins/fhd/'
else:
    skin_path = plugin_path + '/res/skins/hd/'
if os.path.exists('/var/lib/dpkg/status'):
    skin_path = skin_path + 'dreamOs/'


class apList(MenuList):
    def __init__(self, list):
        MenuList.__init__(self, list, True, eListboxPythonMultiContent)

        if screenwidth.width() == 2560:
            self.l.setItemHeight(60)
            textfont = int(38)
            self.l.setFont(0, gFont('Regular', textfont))

        elif screenwidth.width() == 1920:
            self.l.setItemHeight(50)
            textfont = int(32)
            self.l.setFont(0, gFont('Regular', textfont))

        else:
            self.l.setItemHeight(50)
            textfont = int(28)
            self.l.setFont(0, gFont('Regular', textfont))


def apListEntry(name, png):
    res = [name]
    png = os.path.join(plugin_path, 'res/pics/star.png')

    res.append(MultiContentEntryPixmapAlphaTest(pos=(5, 5), size=(50, 50), png=loadPNG(png)))
    if screenwidth.width() == 2560:
        res.append(MultiContentEntryText(pos=(110, 0), size=(950, 50), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
    elif screenwidth.width() == 1920:
        res.append(MultiContentEntryText(pos=(75, 0), size=(750, 50), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
    else:
        res.append(MultiContentEntryText(pos=(70, 0), size=(650, 50), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
    return res


def showlist(data, list):
    idx = 0
    plist = []
    for line in data:
        name = data[idx]
        plist.append(apListEntry(name, idx))
        idx = idx + 1
        list.setList(plist)


class MainApod(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        global _session
        _session = session
        global search_ok
        search_ok = False
        skin = os.path.join(skin_path, 'MainApod.xml')
        with codecs.open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()
        self.setup_title = ('HOME')
        self.setTitle(title_plug)
        self.PicLoad = ePicLoad()
        global tmpimg
        tmpimg = os.path.join('/tmp', 'image.png')
        self.list = []
        self.data = []
        self.urls = []
        self.desc = []
        self['title'] = Label(title_plug)
        self['list'] = self.list
        self['list'] = apList([])
        self['info'] = Label()
        self["poster"] = Pixmap()
        # self['poster'].hide()
        self['key_red'] = Button(_('Back'))
        self['key_green'] = Button()
        self['key_yellow'] = Button(_('Search'))
        self["key_blue"] = Button(_('Info Image'))
        self['Maintainer'] = Label('%s' % Maintener)
        self.currentList = 'list'
        self['actions'] = ActionMap(['EPGSelectActions',
                                     'OkCancelActions',
                                     'DirectionActions',
                                     # 'ButtonSetupActions',
                                     'ColorActions'], {'ok': self.okRun,
                                                       'cancel': self.backhome,
                                                       'red': self.backhome,
                                                       'yellow': self.search_apod,
                                                       'blue': self.prev_blue,
                                                       'up': self.up,
                                                       'down': self.down,
                                                       'left': self.left,
                                                       'right': self.right,
                                                       'epg': self.info,
                                                       'info': self.info}, -2)

        self.readJsonTimer = eTimer()
        try:
            self.readJsonTimer_conn = self.readJsonTimer.timeout.connect(self.downloadxmlpage)
        except:
            self.readJsonTimer.callback.append(self.downloadxmlpage)
        self.readJsonTimer.start(200, True)
        self.onLayoutFinish.append(self.load_infos)
        # self.currentList.moveToIndex(0)

    def info(self):
        aboutbox = self.session.open(MessageBox, _('Apod Plugin v.%s\n\n\nThanks:\n@oktus\nCorvoboys - Forum\n\nIf you like the plugin you can offer a coffee:\n\nhttps://ko-fi.com/lululla') % currversion, MessageBox.TYPE_INFO)
        aboutbox.setTitle(_('Info Apod'))

    def search_apod(self):
        self.session.openWithCallback(
            self.filterM3u,
            VirtualKeyBoard,
            title=_("Filter this category..."),
            text='')

    def filterM3u(self, result):
        global search_ok
        if result:
            try:
                self.data = []
                self.urls = []
                for item in itemlist:
                    name = item.split('###')[0]
                    url = item.split('###')[1]
                    if result.lower() in str(name).lower():
                        search_ok = True
                        urlx = url.replace('%0a', '').replace('%0A', '')
                        self.data.append(str(name))
                        self.urls.append(str(urlx))
                        showlist(self.data, self['list'])
                if len(self.data) < 0:
                    _session.open(MessageBox, _('No Image Map found in search!!!'), MessageBox.TYPE_INFO, timeout=5)
                    return
                else:
                    showlist(self.data, self['list'])
                self.load_infos()
            except Exception as error:
                print(error)
                self['info'].setText('Error')

    def downloadxmlpage(self):
        url = 'http://apod.nasa.gov/apod/archivepix.html'
        if PY3:
            url = url.encode()
        if os.path.exists('/var/lib/dpkg/info'):
            self.data = checkGZIP(url)
            self._gotPageLoad(self.data)
        else:
            getPage(url).addCallback(self._gotPageLoad).addErrback(self.errorLoad)

    def errorLoad(self, error):
        print('are here error:', str(error))
        self['info'].setText(_('Addons Download Failure\nNo internet connection or server down !'))

    def _gotPageLoad(self, page):
        global search_ok
        search_ok = False
        self.data = []
        self.urls = []
        self.desc = []
        items = []
        data = page.decode('utf-8', errors='ignore')
        try:
            regexnasa = r'(\d{4} \w+ \d{2}):\s*<a href="(ap\d{6}\.html)">(.*?)<\/a><br>'
            matches = re.compile(regexnasa, re.DOTALL).findall(data)
            for data, url, desc in matches:
                url = 'https://apod.nasa.gov/apod/' + str(url)
                data = data + ' ' + str(desc)
                self.data.append(str(data))
                self.urls.append(str(url))
                self.desc.append(str(desc))
                item = data + "###" + url + '\n'
                items.append(item)
            global itemlist
            itemlist = items
            showlist(self.data, self['list'])
            self.load_infos()
            # self['list'].moveToIndex(0)
        except Exception as e:
            print("Error: can't find file or read data", e)
        return

    def load_infos(self):
        i = len(self.data)
        if i <= 0:
            return
        if self["poster"].instance:
            self["poster"].instance.setPixmapFromFile(tmpImg)
        try:
            global tmpimg
            idx = self['list'].getSelectionIndex()
            if idx < 0 or idx >= len(self.urls):
                print("Indice non valido:", idx)
                return
            info = self.data[idx]
            self.urlz = self.urls[idx]
            if info != '' or info != 'None' or info is not None:
                self['info'].setText(str(info))
                self.downloadx(self.urlz)
        except Exception as e:
            print('error info:', e)

    def downloadx(self, url=None):
        tmpimg = os.path.join('/tmp', 'image.png')
        if os.path.exists(tmpimg):
            os.remove(tmpimg)
        url = self.urlz if url is None else url
        if PY3:
            url = url.encode()
        if sys.version_info[0] < 3:
            url = url.decode('utf-8', errors='ignore')
        else:
            url = url
        if os.path.exists('/var/lib/dpkg/info'):
            data = checkGZIP(url)
            self._gotPa(data)
        else:
            getPage(url).addCallback(self._gotPa).addErrback(self.errorLoad)

    def _gotPa(self, page):
        if isinstance(page, bytes):
            data = page.decode('utf-8', errors='ignore')
        else:
            data = page
        try:
            regexnasa = r'<IMG SRC="(image\/\d+\/[^"]+\.(?:jpg|png))"\s+alt="([^"]+)"'
            matches = re.compile(regexnasa, re.DOTALL).findall(data)
            # if matches:
            url, desc = matches[0]
            self.url = 'https://apod.nasa.gov/apod/' + str(url)
            self.loadDefaultImage()
        except Exception as e:
            print("Errore durante il caricamento dei dati:", e)
            return False

    def loadDefaultImage(self, failure=None):
        try:
            global tmpimg, tmpImg
            tmpimg = os.path.join('/tmp', 'image.png')
            if os.path.exists(tmpimg):
                os.remove(tmpimg)
            import requests as r
            from PIL import Image
            if failure:
                print("*** failure *** %s" % failure)
            image_request = r.get(self.url)
            image_request.raise_for_status()
            # image_extension = os.path.splitext(self.url)[1]
            # image_path = f'/tmp/image{image_extension}'
            with open(tmpimg, 'wb') as img:
                img.write(image_request.content)
            im = Image.open(tmpimg).convert("RGBA")
            size = [450, 250]
            im.thumbnail(size, Image.LANCZOS)
            im.save(tmpimg)
            if tmpimg is not None and os.path.exists(tmpimg) and os.path.getsize(tmpimg) > 50:
                tmpimg = tmpimg
            else:
                tmpimg = tmpImg
            self["poster"].instance.setPixmapFromFile(tmpimg)
            # return True
        except r.exceptions.RequestException as e:
            print("Errore durante il download dell'immagine:", e)
        except Exception as e:
            print("Errore inaspettato:", e)

    def up(self):
        self[self.currentList].up()
        self.load_infos()

    def down(self):
        self[self.currentList].down()
        self.load_infos()

    def left(self):
        self[self.currentList].pageUp()
        self.load_infos()

    def right(self):
        self[self.currentList].pageDown()
        self.load_infos()

    def prev_blue(self):
        i = len(self.data)
        if i <= 0:
            return
        idx = self['list'].getSelectionIndex()
        url = self.urls[idx]
        self.named = self.data[idx]
        if PY3:
            url = url.encode()
        if os.path.exists('/var/lib/dpkg/info'):
            self.data = checkGZIP(url)
            self.key_blue(self.data)
        else:
            getPage(url).addCallback(self.key_blue).addErrback(self.errorLoad)

    def key_blue(self, page):
        self.url = ''
        self.descx = None
        data = page.decode('utf-8', errors='ignore')
        regexnasa = r'alt="([^"]+)"'
        matches = re.compile(regexnasa, re.DOTALL).findall(data)
        for desc in matches:
            self.descx = str(self.named) + '\n\n' + str(desc) + '\n\n' + 'Archive here https://apod.nasa.gov/apod'
        if self.descx is not None:
            aboutbox = self.session.open(MessageBox, self.descx, MessageBox.TYPE_INFO, timeout=10)
        else:
            aboutbox = self.session.open(MessageBox, "No Descriptions for this image\nOk or Exit for return to list", MessageBox.TYPE_INFO, timeout=10)
        aboutbox.setTitle(_('Info Apod'))

    def okRun(self):
        i = len(self.data)
        if i <= 0:
            return
        idx = self['list'].getSelectionIndex()
        if idx < 0 or idx >= len(self.urls):
            print("Indice non valido:", idx)
            return
        url = self.urls[idx]
        if url:
            try:
                self.session.open(MainApod2, url)
            except Exception as e:
                print("Errore nell'aprire l'URL:", e)
                self.session.open(MessageBox, _('Errore nell\'apertura dell\'immagine!'), MessageBox.TYPE_ERROR)
        else:
            print("URL non valido:", url)
            self.session.open(MessageBox, _('URL non valido!'), MessageBox.TYPE_ERROR)

    def backhome(self):
        if search_ok is True:
            self.downloadxmlpage()
        else:
            tmpimg = os.path.join('/tmp', 'image.png')
            if os.path.exists(tmpimg):
                os.remove(tmpimg)
            self.close()


class MainApod2(Screen):
    def __init__(self, session, url=None):
        self.session = session
        Screen.__init__(self, session)
        global _session
        _session = session
        skin = os.path.join(skin_path, 'MainApod2.xml')
        with codecs.open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()
        self["poster"] = Pixmap()
        self.url = url
        self['text'] = Label()
        self['actions'] = ActionMap(['OkCancelActions',
                                     'DirectionActions',
                                     'ColorActions'], {'ok': self.clsgo,
                                                       'cancel': self.clsgo,
                                                       'red': self.clsgo,
                                                       'green': self.clsgo}, -1)
        self.onLayoutFinish.append(self.downloadxmlpage)

    def downloadxmlpage(self, url=None):
        tmpimg = os.path.join('/tmp', 'image.png')
        if os.path.exists(tmpimg):
            os.remove(tmpimg)
        url = self.url if url is None else url
        if PY3:
            url = url.encode()
        print('my 2 url download=', url)
        if os.path.exists('/var/lib/dpkg/info'):
            self.data = checkGZIP(url)
            self._gotPageLoad(self.data)
        else:
            getPage(url).addCallback(self._gotPageLoad).addErrback(self.errorLoad)

    def errorLoad(self, error):
        print('are here error:', str(error))
        self['info'].setText(_('Addons Download Failure\nNo internet connection or server down !'))

    def _gotPageLoad(self, page):
        self.desc = 'Hello!!'
        data = page.decode('utf-8', errors='ignore')
        try:
            regexnasa = r'<IMG SRC="(image\/\d+\/[^"]+\.(?:jpg|png))"\s+alt="([^"]+)"'
            matches = re.compile(regexnasa, re.DOTALL).findall(data)
            if matches:
                url, desc = matches[0]
                self.url = 'https://apod.nasa.gov/apod/' + str(url)
                self.desc = str(desc)
                self.loadDefaultImage()
            else:
                print("No Image")
                self['info'].setText(_('Nessuna immagine trovata.'))
        except Exception as e:
            print("Errore durante il caricamento dei dati:", e)

    def loadDefaultImage(self, failure=None):
        try:
            global tmpimg, tmpImg
            tmpimg = os.path.join('/tmp', 'image.png')
            if os.path.exists(tmpimg):
                os.remove(tmpimg)

            import requests as r
            from PIL import Image
            if failure:
                print("*** failure *** %s" % failure)
            continfo = f"{self.desc}\nhttps://apod.nasa.gov\n\n"
            self['text'].setText(continfo)
            image_request = r.get(self.url)
            image_request.raise_for_status()
            # image_extension = os.path.splitext(self.url)[1]
            # image_path = f'/tmp/image{image_extension}'
            with open(tmpimg, 'wb') as img:
                img.write(image_request.content)
            im = Image.open(tmpimg).convert("RGBA")
            size = [450, 250]
            '''
            # size = [1280, 720]
            # screen_width = screenwidth.width()
            # if screen_width in (1920, 2560):
                # size = [1920, 1080]
            '''
            im.thumbnail(size, Image.LANCZOS)
            im.save(tmpimg)
            if tmpimg is not None and os.path.exists(tmpimg) and os.path.getsize(tmpimg) > 50:
                tmpimg = tmpimg
            else:
                tmpimg = tmpImg
            self["poster"].instance.setPixmapFromFile(tmpimg)
        except r.exceptions.RequestException as e:
            print("Errore durante il download dell'immagine:", e)
        except Exception as e:
            print("Errore inaspettato:", e)

    def clsgo(self):
        self.close()

    def DecodePicture(self, PicInfo=None):
        self.scale = AVSwitch().getFramebufferScale()
        self.PicLoad = ePicLoad()
        ptr = self.PicLoad.getData()
        if ptr is not None:
            self['poster'].instance.setPixmap(ptr)


class startApod(Screen):
    def __init__(self, session, url=None):
        self.session = session
        global _session
        _session = session
        skin = os.path.join(skin_path, 'MainApod2.xml')
        with codecs.open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()
        Screen.__init__(self, session)
        self["poster"] = Pixmap()
        self.url = url
        self['text'] = Label()
        self['actions'] = ActionMap(['OkCancelActions',
                                     'DirectionActions',
                                     'ColorActions'], {'ok': self.clsgo,
                                                       'cancel': self.clsgo,
                                                       'red': self.clsgo,
                                                       'green': self.clsgo}, -1)
        self.onLayoutFinish.append(self.loadDefaultImage)

    def loadDefaultImage(self, failure=None):
        try:
            import os
            import requests as r
            from PIL import Image
            tmpimg = os.path.join('/tmp', 'image.png')
            if os.path.exists('/tmp/image.png'):
                os.remove('/tmp/image.png')
            if self.url is None:
                self.url = "https://api.nasa.gov/planetary/apod?api_key=YclxOjDyAU3GNzZH2wwcIglfoLcV1WvujcUtncet"
            response = r.get(self.url)
            response.raise_for_status()  # Controllo errori HTTP
            data = response.json()
            self.date = data.get('date')
            self.titlex = data.get('title')
            image_url = data.get('url')
            self.descr = data.get('explanation')
            self.copyr = data.get('copyright')
            continfo = f"{self.date}\n\n{self.descr}\n{self.copyr}\nhttps://apod.nasa.gov\n\n"
            self['text'].setText(continfo)
            image_request = r.get(image_url)
            image_request.raise_for_status()  # Controllo errori HTTP
            # image_extension = os.path.splitext(image_url)[1]
            # image_path = f'/tmp/image{image_extension}'
            if not os.path.exists('/tmp'):
                os.makedirs('/tmp')
            with open(tmpimg, 'wb') as img:
                img.write(image_request.content)
            im = Image.open(tmpimg).convert("RGBA")
            im = Image.open(tmpimg).convert("RGBA")
            size = [1280, 720]
            screen_width = screenwidth.width()
            if screen_width in (1920, 2560):
                size = [1920, 1080]
            im.thumbnail(size, Image.Resampling.LANCZOS)
            im.save(tmpimg)
            if tmpimg is not None and os.path.exists(tmpimg) and os.path.getsize(tmpimg) > 50:
                tmpimg = tmpimg
            else:
                tmpimg = tmpImg
            self["poster"].instance.setPixmapFromFile(tmpimg)
        except r.exceptions.RequestException as e:
            print("An error occurred while fetching data:", e)
            self['text'].setText(_('Errore durante il download dell\'immagine.'))
        except Exception as e:
            print("An unexpected error occurred:", e)
            self['text'].setText(_('Errore inaspettato.'))
        '''
        {
            "copyright": "\nAnirudh Shastry\n",
            "date": "2024-08-28",
            "explanation": "When can you see a black hole, a tulip, and a swan all at once? At night -- if the timing is right,\
            # and if your telescope is pointed in the right direction.  The complex and beautiful Tulip Nebula blossoms about 8,000\
            # light-years away toward the constellation of Cygnus the Swan.  Ultraviolet radiation from young energetic stars at\
            # the edge of the Cygnus OB3 association, including O star HDE 227018, ionizes the atoms and powers the emission from the\
            # Tulip Nebula.  Stewart Sharpless cataloged this nearly 70 light-years across reddish glowing cloud of interstellar gas and\
            # dust in 1959, as Sh2-101. Also in the featured field of view is the black hole Cygnus X-1, which to be a microquasar because\
            # it is one of strongest X-ray sources in planet Earth's sky. Blasted by powerful jets from a lurking black hole, its fainter \
            # bluish curved shock front is only faintly visible beyond the cosmic Tulip's petals, near the right side of the frame.
            # Back to School? Learn Science with NASA",
            "hdurl": "https://apod.nasa.gov/apod/image/2408/Tulip_Shastry_6144.jpg",
            "media_type": "image",
            "service_version": "v1",
            "title": "Tulip Nebula and Black Hole Cygnus X-1",
            "url": "https://apod.nasa.gov/apod/image/2408/Tulip_Shastry_1080.jpg"
        }
        '''

    def clsgo(self):
        try:
            self.session.openWithCallback(self.close, MainApod)
        except Exception as e:
            print('error on exit=', e)
            self.close()


def main(session, **kwargs):
    try:
        session.open(startApod, None)
    except:
        import traceback
        traceback.print_exc()
        pass


def Plugins(**kwargs):
    icona = 'logo.png'
    result = [PluginDescriptor(name=name_plug, description=title_plug, where=PluginDescriptor.WHERE_PLUGINMENU, icon=icona, fnc=main)]
    return result

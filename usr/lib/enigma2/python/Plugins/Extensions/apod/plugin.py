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


currversion = '1.2'
title_plug = '..:: Picture of The Day - Nasa %s ::..' % currversion
name_plug = 'Picture of The Day'
Credits = 'Info http://t.me/tivustream'
Maintener = 'Maintener @Lululla'
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
# ================

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
            textfont = int(34)
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
        res.append(MultiContentEntryText(pos=(70, 0), size=(465, 30), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
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
        self.list = []
        self.data = []
        self.urls = []
        self.desc = []
        self['title'] = Label(title_plug)
        self['list'] = self.list
        self['list'] = apList([])
        self['info'] = Label()
        # self["poster"] = Pixmap()
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
            print('have a dreamOs!!!')
            self.data = checkGZIP(url)
            self._gotPageLoad(self.data)
        else:
            print('have a Atv-PLi - etc..!!!')
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
            '''
            if PY3:
                data = data.decode("utf-8")
            else:
                data = data.encode("utf-8")
            if data:
            '''
            # print('content: ', data)
            regexnasa = r'(\d{4} \w+ \d{2}):\s*<a href="(ap\d{6}\.html)">(.*?)<\/a><br>'
            matches = re.compile(regexnasa, re.DOTALL).findall(data)
            for data, url, desc in matches:
                '''
                try:
                    data = datetime.strptime(data, '%Y %B %d')
                except ValueError as e:
                    print('error:', e)
                '''
                url = 'https://apod.nasa.gov/apod/' + str(url)
                data = data + ' ' + str(desc)
                self.data.append(str(data))
                self.urls.append(str(url))
                self.desc.append(str(desc))

                # for search
                item = data + "###" + url + '\n'
                items.append(item)
            # items.sort()
            global itemlist
            itemlist = items
            # end search

            showlist(self.data, self['list'])
            self.load_infos()
            # self['list'].moveToIndex(0)
        except Exception as e:
            print("Error: can't find file or read data", e)
        return

    def load_infos(self):
        try:
            i = len(self.data)
            if i > 0:
                idx = self['list'].getSelectionIndex()
                info = self.data[idx]
                if info != '' or info != 'None' or info is not None:
                    self['info'].setText(str(info))
        except Exception as e:
            print('error info:', e)

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
        if i < 0:
            return
        idx = self['list'].getSelectionIndex()
        url = self.urls[idx]
        self.named = self.data[idx]
        if PY3:
            url = url.encode()
        if os.path.exists('/var/lib/dpkg/info'):
            print('have a dreamOs!!!')
            self.data = checkGZIP(url)
            self.key_blue(self.data)
        else:
            print('have a Atv-PLi - etc..!!!')
            getPage(url).addCallback(self.key_blue).addErrback(self.errorLoad)

    def key_blue(self, page):
        self.url = ''
        self.descx = None
        data = page.decode('utf-8', errors='ignore')
        regexnasa = r'alt="([^"]+)"'
        matches = re.compile(regexnasa, re.DOTALL).findall(data)
        for desc in matches:
            # print('desc is:', str(desc))
            self.descx = str(self.named) + '\n\n' + str(desc) + '\n\n' + 'Archive here https://apod.nasa.gov/apod'
        if self.descx is not None:
            aboutbox = self.session.open(MessageBox, self.descx, MessageBox.TYPE_INFO, timeout=10)
        else:
            aboutbox = self.session.open(MessageBox, "No Descriptions for this image\nOk or Exit for return to list", MessageBox.TYPE_INFO, timeout=10)
        aboutbox.setTitle(_('Info Apod'))

    def okRun(self):
        i = len(self.data)
        if i < 0:
            return
        idx = self['list'].getSelectionIndex()
        url = self.urls[idx]
        self.session.open(MainApod2, url)

    def backhome(self):
        if search_ok is True:
            self.downloadxmlpage()
        else:
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

    def downloadxmlpage(self):
        url = self.url
        if PY3:
            url = url.encode()
        if os.path.exists('/var/lib/dpkg/info'):
            print('have a dreamOs!!!')
            self.data = checkGZIP(url)
            self._gotPageLoad(self.data)
        else:
            print('have a Atv-PLi - etc..!!!')
            getPage(url).addCallback(self._gotPageLoad).addErrback(self.errorLoad)

    def errorLoad(self, error):
        print('are here error:', str(error))
        self['info'].setText(_('Addons Download Failure\nNo internet connection or server down !'))

    def _gotPageLoad(self, page):
        self.url = ''
        self.desc = ''
        data = page.decode('utf-8', errors='ignore')
        try:
            '''
            print('content: ', data)
            <IMG SRC="image/2408/MoonEclipsesSaturn_Sanz_960.jpg"
            alt="A picture of the edge of the Earth's familiar Moon
            takes up the right part of the frame, while a partial image
            of Saturn is visible just behind it on the left.
            Please see the explanation for more detailed information."
            '''
            regexnasa = r'<IMG SRC="(image\/\d+\/[^"]+\.(?:jpg|png))"\s+alt="([^"]+)"'
            matches = re.compile(regexnasa, re.DOTALL).findall(data)
            for url, desc in matches:
                self.url = 'https://apod.nasa.gov/apod/' + str(url)
                self.desc = str(desc)

            self.loadDefaultImage()
        except Exception as e:
            print(e)
            print("Error: can't find file or read data")
        return

    def loadDefaultImage(self, failure=None):
        try:
            import os
            import requests as r
            if failure:
                print("*** failure *** %s" % failure)

            image_request = r.get(self.url)
            image_request.raise_for_status()  # Check for HTTP errors

            # Get the image file extension from the URL
            image_extension = os.path.splitext(self.url)[1]
            image_path = '/tmp/image' + image_extension
            image_path2 = '/tmp/image'
            with open(image_path, 'wb') as img:
                img.write(image_request.content)
            try:
                import Image
            except:
                from PIL import Image, ImageChops
            im = Image.open(image_path).convert("RGBA")

            size = [1280, 720]
            if screenwidth.width() == 2560:
                size = [1920, 1080]
            elif screenwidth.width() == 1920:
                size = [1920, 1080]

            im = Image.open(image_path).convert("RGBA")
            try:
                im.thumbnail(size, Image.Resampling.LANCZOS)
            except:
                im.thumbnail(size, Image.ANTIALIAS)
            imagew, imageh = im.size

            if imagew < size[0]:
                ratio = size[0] / imagew
                try:
                    im = im.resize((int(imagew * ratio), int(imageh * ratio)), Image.Resampling.LANCZOS)
                except:
                    im = im.resize((int(imagew * ratio), int(imageh * ratio)), Image.ANTIALIAS)

            imagew, imageh = im.size
            bg = Image.new("RGBA", size, (255, 255, 255, 0))
            im_alpha = im.convert("RGBA").split()[-1]
            bgwidth, bgheight = bg.size
            bg_alpha = bg.convert("RGBA").split()[-1]
            temp = Image.new("L", (bgwidth, bgheight), 0)
            temp.paste(im_alpha, (int((bgwidth - imagew) / 2), int((bgheight - imageh) / 2)), im_alpha)
            bg_alpha = ImageChops.screen(bg_alpha, temp)
            im.paste(im, (int((bgwidth - imagew) / 2), int((bgheight - imageh) / 2)))

            # image_path =  '/tmp/image'
            im.save(image_path2 + ".png", "PNG")
            tmpimg = image_path2 + '.png'
            self["poster"].instance.setPixmapFromFile(os.path.join('tmp', tmpimg))

            # description image
            continfo = str(self.desc) + '\n'
            continfo += _('https://apod.nasa.gov') + '\n\n'
            print('continfo=', continfo)
            try:
                self['text'].setText(continfo)
            except:
                self['text'].setText(_('\n\n' + 'Error downloading data!'))

        except r.exceptions.RequestException as e:
            print("An error occurred while fetching data: %s" % e)
        except Exception as e:
            print("An unexpected error occurred: %s" % e)

    def clsgo(self):
        self.close()


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
            if failure:
                print("*** failure *** %s" % failure)

            if self.url is None:
                self.url = "https://api.nasa.gov/planetary/apod?api_key=YclxOjDyAU3GNzZH2wwcIglfoLcV1WvujcUtncet"

            response = r.get(self.url)
            response.raise_for_status()  # Check for HTTP errors

            data = response.json()
            '''
            # if PY3:
                # data = page.decode("utf-8")
            # else:
                # data = page.encode("utf-8")
            '''
            self.date = data.get('date')
            self.titlex = data.get('title')
            image_url = data.get('url')
            self.descr = data.get('explanation')
            self.copyr = data.get('copyright')

            image_request = r.get(image_url)
            image_request.raise_for_status()  # Check for HTTP errors

            # Get the image file extension from the URL
            image_extension = os.path.splitext(image_url)[1]
            image_path = '/tmp/image' + image_extension
            image_path2 = '/tmp/image'
            with open(image_path, 'wb') as img:
                img.write(image_request.content)
            try:
                import Image
            except:
                from PIL import Image, ImageChops
            im = Image.open(image_path).convert("RGBA")

            size = [1280, 720]
            if screenwidth.width() == 2560:
                size = [1920, 1080]
            elif screenwidth.width() == 1920:
                size = [1920, 1080]

            im = Image.open(image_path).convert("RGBA")

            try:
                im.thumbnail(size, Image.Resampling.LANCZOS)
            except:
                im.thumbnail(size, Image.ANTIALIAS)
            imagew, imageh = im.size

            if imagew < size[0]:
                ratio = size[0] / imagew
                try:
                    im = im.resize((int(imagew * ratio), int(imageh * ratio)), Image.Resampling.LANCZOS)
                except:
                    im = im.resize((int(imagew * ratio), int(imageh * ratio)), Image.ANTIALIAS)

            imagew, imageh = im.size

            bg = Image.new("RGBA", size, (255, 255, 255, 0))
            im_alpha = im.convert("RGBA").split()[-1]
            bgwidth, bgheight = bg.size
            bg_alpha = bg.convert("RGBA").split()[-1]
            temp = Image.new("L", (bgwidth, bgheight), 0)
            temp.paste(im_alpha, (int((bgwidth - imagew) / 2), int((bgheight - imageh) / 2)), im_alpha)
            bg_alpha = ImageChops.screen(bg_alpha, temp)
            im.paste(im, (int((bgwidth - imagew) / 2), int((bgheight - imageh) / 2)))

            # image_path =  '/tmp/image'
            im.save(image_path2 + ".png", "PNG")

            tmpimg = image_path2 + '.png'
            self["poster"].instance.setPixmapFromFile(os.path.join('tmp', tmpimg))

            continfo = str(self.date) + '\n\n'
            continfo += str(self.descr) + '\n'
            continfo += str(self.copyr) + '\n'
            continfo += _('https://apod.nasa.gov') + '\n\n'
            # print('continfo=', continfo)
            try:
                self['text'].setText(continfo)
            except:
                self['text'].setText(_('\n\n' + 'Error downloading data!'))

            # self.decodeImage(image_path)
        except r.exceptions.RequestException as e:
            print("An error occurred while fetching data: %s" % e)
        except Exception as e:
            print("An unexpected error occurred: %s" % e)
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
        self.session.openWithCallback(self.close, MainApod)


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

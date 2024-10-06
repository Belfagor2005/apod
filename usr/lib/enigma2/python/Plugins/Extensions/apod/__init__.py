#!/usr/bin/python
# -*- coding: utf-8 -*-

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext
import os
import sys


PluginLanguageDomain = 'apod'
PluginLanguagePath = 'Extensions/apod/res/locale'
plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/apod'
isDreamOS = False
if os.path.exists("/usr/bin/apt-get"):
    isDreamOS = True


def trace_error():
    import traceback
    try:
        traceback.print_exc(file=sys.stdout)
        traceback.print_exc(file=open('/tmp/traceback.log', 'a'))
    except:
        pass


def logdata(name='', data=None):
    try:
        data = str(data)
        fp = open('/tmp/revolution3.log', 'a')
        fp.write(str(name) + ': ' + data + "\n")
        fp.close()
    except:
        trace_error()
        pass


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


'''
def checkGZIP(url, retries=3, initial_timeout=5):
    import sys
    import socket
    if sys.version_info[0] == 3:
        from urllib.request import (urlopen)
        from urllib.error import URLError
        # unicode = str
        PY3 = True
    else:
        from urllib2 import (urlopen)
        from urllib2 import URLError
    timeout = initial_timeout
    for i in range(retries):
        try:
            fp = urlopen(url, timeout=timeout)
            lines = fp.readlines()
            fp.close()
            labeltext = ""
            for line in lines:
                if PY3:
                    line = line.decode()  # Decode bytes to str in Python 3
                labeltext += str(line)
            return labeltext
        except socket.timeout:
            print("Attempt failed: The connection timed out after %s seconds." % timeout)
            timeout *= 2  # Double the timeout for the next attempt
        except URLError as e:
            print("URL Error:", e)
            break
        except Exception as e:
            print("Error:", e)
            break
    return None
'''


'''
def checkGZIP(url, max_retries=3, base_delay=1):
    import time
    import socket
    import sys

    if sys.version_info[0] == 3:
        from urllib.request import (urlopen, Request)
        from urllib.error import URLError
    else:
        from urllib2 import (urlopen, Request)
        from urllib2 import URLError

    for attempt in range(max_retries):
        try:
            req = Request(url)
            req.add_header('User-Agent', AgentRequest)
            start_time = time.time()
            response = urlopen(req, None, 10)

            elapsed_time = time.time() - start_time
            print('elapsed_time:', elapsed_time)

            if response.getcode() == 200:
                content = response.read().decode('utf-8')
                return content
            else:
                print("URL returned status code:", response.getcode)
                return None
        except URLError as e:
            if isinstance(e.reason, socket.timeout):
                delay = base_delay * (2 ** attempt)
                print("Timeout occurred. Retrying in seconds...", str(delay))
                time.sleep(delay)
            else:
                print("URLError occurred:", str(e))
                return None
    print("Max retries reached.")
    return None
'''

'''
# def checkGZIP(url):
    # url = url
    # from io import StringIO
    # import gzip
    # import requests
    # import sys
    # if sys.version_info[0] == 3:
        # from urllib.request import (urlopen, Request)
    # else:
        # from urllib2 import (urlopen, Request)
    # AgentRequest = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.3'
    # hdr = {"User-Agent": AgentRequest}
    # response = None
    # request = Request(url, headers=hdr)
    # try:
        # response = urlopen(request, timeout=10)
        # if response.info().get('Content-Encoding') == 'gzip':
            # buffer = StringIO(response.read())
            # deflatedContent = gzip.GzipFile(fileobj=buffer)
            # if sys.version_info[0] == 3:
                # return deflatedContent.read().decode('utf-8')
            # else:
                # return deflatedContent.read()
        # else:
            # if sys.version_info[0] == 3:
                # return response.read().decode('utf-8')
            # else:
                # return response.read()

    # except requests.exceptions.RequestException as e:
        # print("Request error:", e)
    # except Exception as e:
        # print("Unexpected error:", e)
    # return None
'''


def checkGZIP(url):
    from io import BytesIO  # Usa BytesIO per la compatibilità
    import gzip
    import requests
    import sys
    if sys.version_info[0] == 3:
        from urllib.request import urlopen, Request
    else:
        from urllib2 import urlopen, Request
    AgentRequest = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.3'
    hdr = {"User-Agent": AgentRequest}
    response = None
    request = Request(url, headers=hdr)
    try:
        response = urlopen(request, timeout=10)
        if response.info().get('Content-Encoding') == 'gzip':
            buffer = BytesIO(response.read())  # Leggi i dati in un buffer di byte
            with gzip.GzipFile(fileobj=buffer) as deflatedContent:  # Decomprimi i dati
                if sys.version_info[0] == 3:
                    return deflatedContent.read().decode('utf-8')  # Decodifica in utf-8 per Python 3
                else:
                    return deflatedContent.read()  # Ritorna i byte per Python 2
        else:
            if sys.version_info[0] == 3:
                return response.read().decode('utf-8')  # Decodifica per Python 3
            else:
                return response.read()  # Ritorna i byte per Python 2
    except requests.exceptions.RequestException as e:
        print("Request error:", e)
    except Exception as e:
        print("Unexpected error:", e)
    return None

# -*- coding: utf-8 -*-
import os
import time
import sys

import xbmc

import urllib, urllib2
import socket
import gzip
import StringIO
import socks
import random

METHOD_PROXY = 1
METHOD_IP_FORWARD = 2

# Windows 8, Internet Explorer 10
USER_AGENT = "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)"

def GetProxy():
    proxy_server = None
    proxy_type_id = 0
    proxy_port = 8080
    proxy_user = None
    proxy_pass = None
    try:
        proxy_server = addon.getSetting(u'proxy_server')
        proxy_type_id = addon.getSetting(u'proxy_type')
        proxy_port = int(addon.getSetting(u'proxy_port'))
        proxy_user = addon.getSetting(u'proxy_user')
        proxy_pass = addon.getSetting(u'proxy_pass')
    except:
        pass

    if   proxy_type_id == u'0': proxy_type = socks.PROXY_TYPE_HTTP_NO_TUNNEL
    elif proxy_type_id == u'1': proxy_type = socks.PROXY_TYPE_HTTP
    elif proxy_type_id == u'2': proxy_type = socks.PROXY_TYPE_SOCKS4
    elif proxy_type_id == u'3': proxy_type = socks.PROXY_TYPE_SOCKS5

    proxy_dns = True

    if proxy_user == u'':
        proxy_user = None

    if proxy_pass == u'':
        proxy_pass = None

    return (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)


#==============================================================================

def SetupProxy():
    addon = sys.modules["__main__"].addon
    
    if int(addon.getSetting(u'proxy_method')) == METHOD_PROXY:
        (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass) = GetProxy()

        self.log(u"Using proxy: type %i rdns: %i server: %s port: %s user: %s pass: %s" % (proxy_type, proxy_dns, proxy_server, proxy_port, u"***", u"***") )

        socks.setdefaultproxy(proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)
        socks.wrapmodule(urllib2)
        


#==============================================================================
class CacheManager:

    def __init__(self):
        self.getFromCache = True
        self.gotFromCache = False
        self.cacheDir = u""
        self.cacheSize = 20
        self.lastCode = -1

        if hasattr(sys.modules["__main__"], "log"):
            self.log = sys.modules["__main__"].log
        else:
            from utils import log
            self.log = log

    """
    Use the given maxAge on cache attempt. If this attempt fails then try again with maxAge = 0 (don't retrieve from cache)
    """
    def ifCacheMaxAge(self, maxAge):
        if self.getFromCache:
            return maxAge

        return 0

    """
     Log level is debug if we are processes a page from the cache, 
     because we don't want to display errors or halt processing 
     unless we are processing a page directly from the web
    """
    def ifCacheLevel(self, logLevel):
        self.log(u"self: %s" % unicode(self))
        self.log(u"ifCacheLevel(%s)" % unicode(logLevel))
        self.log(u"ifCacheLevel self.getFromCache: %s" % unicode(self.getFromCache))
        if self.getFromCache and self.getGotFromCache():
            self.log(u"return xbmc.LOGDEBUG")
            return xbmc.LOGDEBUG;

        self.log(u"ifCacheLevel return logLevel: %s" % unicode(logLevel))
        return logLevel

    def setGetFromCache(self, getFromCache):
        self.log(u"self: %s" % unicode(self))
        self.getFromCache = getFromCache
        self.log(u"setGetFromCache(%s)" % unicode(self.getFromCache))

    def getGetFromCache(self):
        return self.getFromCache


    def getGotFromCache(self):
        return self._Cache_GetFromFlag()

    # Get url from cache iff 'getFromCache' is True, otherwise get directly from web (maxAge = 0)
    # If the page was not in the cache then set cacheAttempt to False, indicating that the page was
    # retrieved from the web
    def GetURLFromCache(self, url, maxAge, values = None, headers = None):
        self.log(u"GetURLFromCache(%s)" % url, xbmc.LOGDEBUG)
        maxAge = self.ifCacheMaxAge(maxAge)
        self.gotFromCache = False
        return self.GetURL( url, maxAge, values, headers )

    #==============================================================================
    
    def GetLastCode(self):
        return lastCode
    
    #==============================================================================
    
    def SetCacheDir(self,  cacheDir ):
        xbmc.log (u"cacheDir: " + cacheDir, xbmc.LOGDEBUG)    
        self.cacheDir = cacheDir
        if not os.path.isdir(cacheDir):
            os.makedirs(cacheDir)
    
    #==============================================================================
    def _Cache_GetFromFlag(self):
        self.log(u"_Cache_GetFromFlag() - gotFromCache = %s" % unicode(self.gotFromCache))
        return self.gotFromCache
    
    def _CheckCacheDir(self):
        if ( self.cacheDir == u'' ):
            return False
    
        return True
    
    #==============================================================================
    
    def _GetURL_NoCache(self,  url, values, headers):
    
        global lastCode
    
        xbmc.log (u"url: " + url, xbmc.LOGDEBUG)    
    
        SetupProxy()
        repeat = True
        firstTime = True
        addon = sys.modules["__main__"].addon
        FORWARDED_FOR_IP = '79.97.%d.%d' % (random.randint(0, 255), random.randint(0, 254)) 

        while repeat:
            repeat = False
            try:
                # Test socket.timeout
                #raise socket.timeout
                data = None
                if  values is not None:
                    data = urllib.urlencode(values)
                request = urllib2.Request(url, data)
                request.add_header('User-Agent', USER_AGENT)
                
                if int(addon.getSetting(u'proxy_method')) == METHOD_IP_FORWARD:
                    request.add_header('X-Forwarded-For', FORWARDED_FOR_IP)

                if headers is not None:
                    for key in headers:
                        request.add_header(key, headers[key])
                        
                response = urllib2.urlopen(request)

            except ( urllib2.HTTPError ) as err:
                xbmc.log ( u'HTTPError: ' + unicode(err), xbmc.LOGERROR)
                lastCode = err.code
                xbmc.log (u"lastCode: " + unicode(lastCode), xbmc.LOGDEBUG)
                return u''
            except ( urllib2.URLError ) as err:
                xbmc.log ( u'URLError: ' + unicode(err), xbmc.LOGERROR )
                lastCode = -1
                return u''
            except ( socket.timeout ) as exception:
                xbmc.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                if firstTime:
                    xbmc.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                    xbmc.executebuiltin(u'XBMC.Notification(%s, %s)' % (u'Socket timed out', 'Trying again'))
                    repeat = True
                else:
                    """
                    The while loop is normally only processed once.
                    When a socket timeout happens it executes twice.
                    The following code executes after the second timeout.
                    """
                    xbmc.log ( u'Timeout exception: ' + unicode(exception) + ", if you see this msg often consider changing your Socket Timeout settings", xbmc.LOGERROR )
                    raise exception
    
                firstTime = False
    
        lastCode = response.getcode()
        xbmc.log (u"lastCode: " + unicode(lastCode), xbmc.LOGDEBUG)
        
        try:
            if response.info()[u'content-encoding'] == u'gzip':
                xbmc.log (u"gzipped page", xbmc.LOGDEBUG)
                gzipper = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
                return gzipper.read()
        except KeyError:
            pass
        
        return response.read()
    
    #==============================================================================
    
    def CachePage(self, url, data, values):
        global lastCode
    
        if lastCode <> 404 and data is not None and len(data) > 0:    # Don't cache "page not found" pages, or empty data
            xbmc.log (u"Add page to cache", xbmc.LOGDEBUG)

            self._Cache_Add( url, data, values )
    
    def GetPostUrl(self, url, values):
        if values is not None:
            url = url + '_'
            for value in values:
                url = url + value + '=' + values[value]
            
        return url
        
        
    def GetURL(self,  url, maxAgeSeconds=0, values = None, headers = None):
        global lastCode
    
        xbmc.log (u"GetURL: " + url, xbmc.LOGDEBUG)
        # If no cache dir has been specified then return the data without caching
        if self._CheckCacheDir() == False:
            xbmc.log (u"Not caching HTTP", xbmc.LOGDEBUG)
            return self._GetURL_NoCache( url, values, headers)
    
        if ( maxAgeSeconds > 0 ):
            xbmc.log (u"maxAgeSeconds: " + unicode(maxAgeSeconds), xbmc.LOGDEBUG)
            # Is this URL in the cache?
            cachedURLTimestamp = self._Cache_GetURLTimestamp( url, values )
            if ( cachedURLTimestamp > 0 ):
                xbmc.log (u"cachedURLTimestamp: " + unicode(cachedURLTimestamp), xbmc.LOGDEBUG)
                # We have file in cache, but is it too old?
                if ( (time.time() - cachedURLTimestamp) > maxAgeSeconds ):
                    xbmc.log (u"Cached version is too old", xbmc.LOGDEBUG)
                    # Too old, so need to get it again
                    data = self._GetURL_NoCache( url, values, headers)
    
                    # Cache it
                    self.CachePage(url, data, values)
    
                    # Cache size maintenance
                    self._Cache_Trim
    
                    # Return data
                    return data
                else:
                    xbmc.log (u"Get page from cache", xbmc.LOGDEBUG)
                    # Get it from cache
                    data = self._Cache_GetData( url, values )
                    
                    if (data <> 0):
                        return data
                    else:
                        self.log(u"Error retrieving page from cache. Zero length page. Retrieving from web.")
        
        # maxAge = 0 or URL not in cache, so get it
        data = self._GetURL_NoCache( url, values, headers)
        self.CachePage(url, data, values)
    
        # Cache size maintenance
        self._Cache_Trim
        # Return data
        return data
    
    #==============================================================================
    
    def _Cache_GetURLTimestamp(self,  url, values ):
        cacheKey = self._Cache_CreateKey( url, values )
        cacheFileFullPath = os.path.join( self.cacheDir, cacheKey )
        if ( os.path.isfile( cacheFileFullPath ) ):
            return os.path.getmtime(cacheFileFullPath)
        else:
            return 0
    
    #==============================================================================
    
    def _Cache_GetData(self,  url, values ):
        global lastCode
        lastCode = 200
        cacheKey = self._Cache_CreateKey( url, values )
        cacheFileFullPath = os.path.join( self.cacheDir, cacheKey )
        xbmc.log (u"Cache file: %s" % cacheFileFullPath, xbmc.LOGDEBUG)
        f = file(cacheFileFullPath, u"r")
        data = f.read()
        f.close()
    
        if len(data) == 0:
            os.remove(cacheFileFullPath)
    
        self.gotFromCache = True
        return data
    
    #==============================================================================
    
    def _Cache_Add(self,  url, data, values ):
        cacheKey = self._Cache_CreateKey( url, values )
        cacheFileFullPath = os.path.join( self.cacheDir, cacheKey )
        xbmc.log (u"Cache file: %s" % cacheFileFullPath, xbmc.LOGDEBUG)
        f = file(cacheFileFullPath, u"w")
        f.write(data)
        f.close()
    
    #==============================================================================
    
    def _Cache_CreateKey(self,  url, values ):
        try:
            if values is not None:
                url = url + u'_'
                for value in values:
                    url = url + value + '=' + unicode(values[value])
            
            self.log("url: " + url)
            from hashlib import md5
            return md5(url).hexdigest()
        except:
            import md5
            self.log("url to be hashed: " + url)
            return  md5.new(url).hexdigest()
    
    #==============================================================================
    
    def _Cache_Trim(self):
        files = glob.glob( self.cacheDir )
        if ( len(files) > self.cacheSize ):
            oldestFile = self.get_oldest_file( files )
            cacheFileFullPath = os.path.join( self.cacheDir, oldestFile )
            if os.path.exists(cacheFileFullPath):
                os.remove(cacheFileFullPath)
    
    #==============================================================================
    
    """ 
    Find and return the oldest file of input file names.
    Only one wins tie. Values based on time distance from present.
    Use of `_invert` inverts logic to make this a youngest routine,
    to be used more clearly via `get_youngest_file`.
    """
    def get_oldest_file(self, files, _invert=False):
        if _invert:
            gt = operator.lt
        else:
            gt = operator.gt
        # Check for empty list.
        if not files:
            return None
        # Raw epoch distance.
        now = time.time()
        # Select first as arbitrary sentinel file, storing name and age.
        oldest = files[0], now - os.path.getctime(files[0])
        # Iterate over all remaining files.
        for f in files[1:]:
            age = now - os.path.getctime(f)
            if gt(age, oldest[1]):
                # Set new oldest.
                oldest = f, age
        # Return just the name of oldest file.
        return oldest[0]

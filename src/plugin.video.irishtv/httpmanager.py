# -*- coding: utf-8 -*-
import os
import time
import sys

import xbmc

import urllib, urllib2
import httplib
import socket
import gzip
import StringIO
import socks
import random
import glob
import re

METHOD_PROXY = 1
METHOD_IP_FORWARD = 2

# Windows 8, Internet Explorer 10
USER_AGENT = "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)"

def GetProxy(addon):
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
    except ( Exception ) as exception:
        raise exception

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
    log = sys.modules["__main__"].log
    
    log("addon.getSetting(u'proxy_method') " + addon.getSetting(u'proxy_method'))
    
    if int(addon.getSetting(u'proxy_method')) == METHOD_PROXY:
        try:
            (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass) = GetProxy(addon)
    
            log(u"Using proxy: type %i rdns: %i server: %s port: %s user: %s pass: %s" % (proxy_type, proxy_dns, proxy_server, proxy_port, u"***", u"***") )
    
            socks.setdefaultproxy(proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)
            socks.wrapmodule(urllib2)
            socks.wrapmodule(httplib)
        except ( Exception ) as exception:
            log(u"Error processing up proxy settings", xbmc.LOGERROR)
            log(u"Exception: " + exception.me, xbmc.LOGERROR)
            
            


#==============================================================================
class HttpManager:

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

    def PostBinary(self, site, path, data, headers = None):
        self.log(u"(%s)" % (site + path), xbmc.LOGDEBUG)

        SetupProxy()
        repeat = True
        firstTime = True
        addon = sys.modules["__main__"].addon

        while repeat:
            repeat = False
            try:
                if site.startswith("http://"):
                    site = site[7:]
                
                headers = self.PrepareHeaders(addon, headers)

                self.log("headers: " + repr(headers))
                
                conn = httplib.HTTPConnection(site)
                conn.request("POST", path, data, headers)
                response = conn.getresponse()
            except ( httplib.HTTPException ) as exception:
                self.log ( u'HTTPError: ' + unicode(exception), xbmc.LOGERROR)
                raise exception
            except ( socket.timeout ) as exception:
                self.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                if firstTime:
                    self.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                    xbmc.executebuiltin(u'XBMC.Notification(%s, %s)' % (u'Socket timed out', 'Trying again'))
                    repeat = True
                else:
                    """
                    The while loop is normally only processed once.
                    When a socket timeout happens it executes twice.
                    The following code executes after the second timeout.
                    """
                    self.log ( u'Timeout exception: ' + unicode(exception) + ", if you see this msg often consider changing your Socket Timeout settings", xbmc.LOGERROR )
                    raise exception
    
                firstTime = False
    
        self.log (u"response.status: " + unicode(response.status), xbmc.LOGDEBUG)
        
        if response.getheader(u'content-encoding', u'') == u'gzip':
            self.log (u"gzipped page", xbmc.LOGDEBUG)
            gzipper = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
            return gzipper.read()
        
        return response.read()

    """
    Get url from cache iff 'getFromCache' is True, otherwise get directly from web (maxAge = 0)
    If the page was not in the cache then set cacheAttempt to False, indicating that the page was
    retrieved from the web
    """
    def GetWebPage(self, url, maxAge, values = None, headers = None):
        self.log(u"GetWebPage(%s)" % url, xbmc.LOGDEBUG)
        maxAge = self.ifCacheMaxAge(maxAge)
        self.gotFromCache = False
        return self.GetURL( url, maxAge, values, headers )

    #==============================================================================
    
    def GetWebPageDirect(self, url, values = None, headers = None):
        self.log(u"GetWebPageDirect(%s)" % url, xbmc.LOGDEBUG)
        return self.GetWebPage(url, 0, values, headers)

    #==============================================================================
    
    def GetLastCode(self):
        return lastCode
    
    #==============================================================================
    
    def SetCacheDir(self,  cacheDir ):
        self.log (u"cacheDir: " + cacheDir, xbmc.LOGDEBUG)    
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
        response = self.GetHTTPResponse(url, values, headers)

        if u'content-encoding' in response.info() and response.info()[u'content-encoding'] == u'gzip':
            self.log (u"gzipped page", xbmc.LOGDEBUG)
            gzipper = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
            return gzipper.read()
        
        return response.read()
        
    
    def GetHTTPResponse(self,  url, values = None, headers = None):
        global lastCode
    
        self.log (u"url: " + url, xbmc.LOGDEBUG)    
    
        SetupProxy()
        repeat = True
        firstTime = True
        addon = sys.modules["__main__"].addon

        while repeat:
            repeat = False
            try:
                # Test socket.timeout
                #raise socket.timeout
                postData = None
                if values is not None:
                    postData = urllib.urlencode(values)
                
                headers = self.PrepareHeaders(addon, headers)
                
                self.log("headers: " + repr(headers), xbmc.LOGDEBUG)
                
                request = urllib2.Request(url, postData, headers)
                response = urllib2.urlopen(request)

            except ( urllib2.HTTPError ) as err:
                self.log ( u'HTTPError: ' + unicode(err), xbmc.LOGERROR)
                lastCode = err.code
                self.log (u"lastCode: " + unicode(lastCode), xbmc.LOGDEBUG)
                raise err
            except ( urllib2.URLError ) as err:
                self.log ( u'URLError: ' + unicode(err), xbmc.LOGERROR )
                lastCode = -1
                raise err
            except ( socket.timeout ) as exception:
                self.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                if firstTime:
                    self.log ( u'Timeout exception: ' + unicode(exception), xbmc.LOGERROR )
                    xbmc.executebuiltin(u'XBMC.Notification(%s, %s)' % (u'Socket timed out', 'Trying again'))
                    repeat = True
                else:
                    """
                    The while loop is normally only processed once.
                    When a socket timeout happens it executes twice.
                    The following code executes after the second timeout.
                    """
                    self.log ( u'Timeout exception: ' + unicode(exception) + ", if you see this msg often consider changing your Socket Timeout settings", xbmc.LOGERROR )
                    raise exception
    
                firstTime = False
    
        lastCode = response.getcode()
        self.log (u"lastCode: " + unicode(lastCode), xbmc.LOGDEBUG)

        return response
        
    #==============================================================================
    
    def PrepareHeaders(self, addon, headers):
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers:
            headers['User-Agent'] = USER_AGENT
            
        if int(addon.getSetting(u'proxy_method')) == METHOD_IP_FORWARD:
            ipSegment1 = int(float(addon.getSetting(u'forward_segment1')))
            ipSegment2 = int(float(addon.getSetting(u'forward_segment2')))
            
            forwardedForIP = '%d.%d.%d.%d' % (ipSegment1, ipSegment2, random.randint(0, 255), random.randint(0, 254)) 
            headers['X-Forwarded-For'] = forwardedForIP
            self.log("Using header 'X-Forwarded-For': " + forwardedForIP)
            
        return headers
            
    #==============================================================================
    
    def CachePage(self, url, data, values, expiryTime):
        global lastCode
    
        if lastCode <> 404 and data is not None and len(data) > 0:    # Don't cache "page not found" pages, or empty data
            self.log (u"Add page to cache", xbmc.LOGDEBUG)

            self._Cache_Add( url, data, values, expiryTime )
    
        
    def GetURL(self,  url, maxAgeSeconds=0, values = None, headers = None):
        global lastCode
    
        self.log (u"GetURL: " + url, xbmc.LOGDEBUG)
        # If no cache dir has been specified then return the data without caching
        if self._CheckCacheDir() == False:
            self.log (u"Not caching HTTP", xbmc.LOGDEBUG)
            return self._GetURL_NoCache( url, values, headers)
    
        currentTime = int(round(time.time()))
        
        if ( maxAgeSeconds > 0 ):
            self.log (u"maxAgeSeconds: " + unicode(maxAgeSeconds), xbmc.LOGDEBUG)
            # Is this URL in the cache?
            expiryString = self.GetExpiryTimeForUrl(url, values)
            if expiryString is not None:
                self.log (u"expiryString: " + unicode(expiryString), xbmc.LOGDEBUG)
                # We have file in cache,_GetURL_NoCache but is it too old?
                if currentTime > int(expiryString):
                    self.log (u"Cached version is too old", xbmc.LOGDEBUG)
                    # Too old, so need to get it again
                    data = self._GetURL_NoCache( url, values, headers)
    
                    # Cache it
                    self.CachePage(url, data, values, currentTime + maxAgeSeconds)
    
                    # Cache size maintenance
                    self._Cache_Trim(currentTime)
    
                    # Return data
                    return data
                else:
                    self.log (u"Get page from cache", xbmc.LOGDEBUG)
                    # Get it from cache
                    data = self._Cache_GetData( url, values, expiryString)
                    
                    if (data <> 0):
                        return data
                    else:
                        self.log(u"Error retrieving page from cache. Zero length page. Retrieving from web.")
        
        # maxAge = 0 or URL not in cache, so get it
        data = self._GetURL_NoCache( url, values, headers)

        if maxAgeSeconds > 0:
            self.CachePage(url, data, values, currentTime + maxAgeSeconds)
    
        # Cache size maintenance
        self._Cache_Trim(currentTime)
        # Return data
        return data
    
    #==============================================================================
    
    def GetExpiryTimeForUrl(self, url, values):
        cacheKey = self._Cache_CreateKey( url, values )
        
        return self.GetExpiryTimeStr(cacheKey)
            
    #==============================================================================
    def GetExpiryTimeStr(self, cacheKey):
        files = glob.iglob( self.cacheDir + "/*" )
        for file in files:
            match=re.search( u"%s_(\d{10})" % cacheKey, file)
    
            if match is not None:
                return match.group(1)
        
        return None
            
        
    def _Cache_GetData(self,  url, values, expiryString ):
        global lastCode
        lastCode = 200
        cacheKey = self._Cache_CreateKey( url, values )
        filename = cacheKey + "_" + expiryString
        cacheFileFullPath = os.path.join( self.cacheDir, filename )
        self.log (u"Cache file: %s" % cacheFileFullPath, xbmc.LOGDEBUG)
        f = file(cacheFileFullPath, u"r")
        data = f.read()
        f.close()
    
        if len(data) == 0:
            os.remove(cacheFileFullPath)
    
        self.gotFromCache = True
        return data
    
    #==============================================================================
    
    def _Cache_Add(self,  url, data, values, currentTime ):
        cacheKey = self._Cache_CreateKey( url, values )
        filename = cacheKey + "_" + str(currentTime)
        cacheFileFullPath = os.path.join( self.cacheDir, filename )
        self.log (u"Cache file: %s" % cacheFileFullPath, xbmc.LOGDEBUG)
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
    
    def IsDeleteFile(self, filename, filenameLen, currentTime):
       if (len(filename) != filenameLen):
           self.log("Invalid cache filename: " + filename, xbmc.LOGWARNING)
           return True
       
       match=re.search( u"(.{32})_(\d{10})", filename)

       if match is None:
           self.log("Invalid cache filename: " + filename, xbmc.LOGWARNING)
           return True

       expireTime = int(match.group(2))
       if currentTime > expireTime:
           self.log("Expired cache file: " + filename, xbmc.LOGDEBUG)
           return True

       return False
        
    #==============================================================================
        
    def _Cache_Trim(self, currentTime):
        epochLen = 10
        cacheKeyLen = 32
        filenameLen = cacheKeyLen + epochLen + 1
        
        pathOffset = len(self.cacheDir) + 1
        files = glob.iglob( self.cacheDir + "/*" )
        for fileFullPath in files:
            filename = os.path.basename(fileFullPath)
            if self.IsDeleteFile(filename, filenameLen, currentTime):
                self.log("Deleting cache fileFullPath: " + fileFullPath, xbmc.LOGDEBUG)
                if os.path.exists(fileFullPath):
                    os.remove(fileFullPath)
        
    #==============================================================================

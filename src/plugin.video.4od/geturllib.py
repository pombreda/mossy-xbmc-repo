#/bin/python

import os
import time

import xbmc,xbmcaddon

import urllib2,socket,gzip,StringIO
import socks

__PluginName__  = 'plugin.video.4od'
__addon__ = xbmcaddon.Addon(__PluginName__)

gCacheDir = ""
gCacheSize = 20
gLastCode = -1


#==============================================================================

def GetProxy():
    proxy_server = None
    proxy_type_id = 0
    proxy_port = 8080
    proxy_user = None
    proxy_pass = None
    try:
        proxy_server = __addon__.getSetting('proxy_server')
        proxy_type_id = __addon__.getSetting('proxy_type')
        proxy_port = int(__addon__.getSetting('proxy_port'))
        proxy_user = __addon__.getSetting('proxy_user')
        proxy_pass = __addon__.getSetting('proxy_pass')
    except:
        pass

    if   proxy_type_id == '0': proxy_type = socks.PROXY_TYPE_HTTP_NO_TUNNEL
    elif proxy_type_id == '1': proxy_type = socks.PROXY_TYPE_HTTP
    elif proxy_type_id == '2': proxy_type = socks.PROXY_TYPE_SOCKS4
    elif proxy_type_id == '3': proxy_type = socks.PROXY_TYPE_SOCKS5

    proxy_dns = True

    if proxy_user == '':
	    proxy_user = None

    if proxy_pass == '':
	    proxy_pass = None

    return (proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)


#==============================================================================

def SetupProxy():
        if __addon__.getSetting('proxy_use') == 'true':
		(proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass) = GetProxy()

                xbmc.log("Using proxy: type %i rdns: %i server: %s port: %s user: %s pass: %s" % (proxy_type, proxy_dns, proxy_server, proxy_port, "***", "***") )

		socks.setdefaultproxy(proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)
		socks.wrapmodule(urllib2)

#==============================================================================

def GetLastCode():
	return gLastCode

#==============================================================================

def SetCacheDir( cacheDir ):
	global gCacheDir

	xbmc.log ("cacheDir: " + cacheDir, xbmc.LOGDEBUG)	
	gCacheDir = cacheDir
	if not os.path.isdir(gCacheDir):
		os.makedirs(gCacheDir)

#==============================================================================

def _CheckCacheDir():
	if ( gCacheDir == '' ):
		return False

	return True


#==============================================================================

def _GetURL_NoCache( url ):

	global gLastCode
	xbmc.log ("url: " + url, xbmc.LOGDEBUG)	

	SetupProxy()
	try:

		response = urllib2.urlopen(url)

	except urllib2.HTTPError, err:
		xbmc.log ( 'HTTPError: ' + str(err), xbmc.LOGERROR)

		gLastCode = err.code
		xbmc.log ("gLastCode: " + str(gLastCode), xbmc.LOGDEBUG)
		return ''

	except urllib2.URLError, err:
		xbmc.log ( 'URLError: ' + str(err), xbmc.LOGERROR )
		gLastCode = -1
		return ''


	gLastCode = response.code
	xbmc.log ("gLastCode: " + str(gLastCode), xbmc.LOGDEBUG)

        try:
                if response.info()['content-encoding'] == 'gzip':
        		xbmc.log ("gzipped page", xbmc.LOGDEBUG)
                        gzipper = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
                        return gzipper.read()
        except KeyError:
		pass
	
	return response.read()

#==============================================================================

def CachePage(url, data):
	global gLastCode

	if gLastCode <> 404 and len(data) > 0:	# Don't cache "page not found" pages, or empty data
		xbmc.log ("Add page to cache", xbmc.LOGDEBUG)
		_Cache_Add( url, data )


def GetURL( url, maxAgeSeconds=0 ):
	global gLastCode

	xbmc.log ("GetURL: " + url, xbmc.LOGDEBUG)
	# If no cache dir has been specified then return the data without caching
	if _CheckCacheDir() == False:
       		xbmc.log ("Not caching HTTP", xbmc.LOGDEBUG)
		return _GetURL_NoCache( url )


	if ( maxAgeSeconds > 0 ):
       		xbmc.log ("maxAgeSeconds: " + str(maxAgeSeconds), xbmc.LOGDEBUG)
		# Is this URL in the cache?
		cachedURLTimestamp = _Cache_GetURLTimestamp( url )
		if ( cachedURLTimestamp > 0 ):
	       		xbmc.log ("cachedURLTimestamp: " + str(cachedURLTimestamp), xbmc.LOGDEBUG)
			# We have file in cache, but is it too old?
			if ( (time.time() - cachedURLTimestamp) > maxAgeSeconds ):
	       			xbmc.log ("Cached version is too old", xbmc.LOGDEBUG)
				# Too old, so need to get it again
				data = _GetURL_NoCache( url )

				# Cache it
				CachePage(url, data)

				# Return data
				return data
			else:
	       			xbmc.log ("Get page from cache", xbmc.LOGDEBUG)
				# Get it from cache
				data = _Cache_GetData( url )
				
				if (data <> 0):
					return data
				else:
					xbmc.log("Error retrieving page from cache. Zero length page. Retrieving from web.")
	
	# maxAge = 0 or URL not in cache, so get it
	data = _GetURL_NoCache( url )
	CachePage(url, data)

	# Cache it
	if gLastCode <> 404 and len(data) > 0:	# Don't cache "page not found" pages, or empty data
		xbmc.log ("Add page to cache", xbmc.LOGDEBUG)
		_Cache_Add( url, data )

	# Cache size maintenance
	_Cache_Trim
	# Return data
	return data

#==============================================================================

def _Cache_GetURLTimestamp( url ):
	cacheKey = _Cache_CreateKey( url )
	cacheFileFullPath = os.path.join( gCacheDir, cacheKey )
	if ( os.path.isfile( cacheFileFullPath ) ):
		return os.path.getmtime(cacheFileFullPath)
	else:
		return 0

#==============================================================================

def _Cache_GetData( url ):
	global gLastCode
	gLastCode = 200
	cacheKey = _Cache_CreateKey( url )
	cacheFileFullPath = os.path.join( gCacheDir, cacheKey )
	f = file(cacheFileFullPath, "r")
	data = f.read()
	f.close()

	if len(data) == 0:
		os.remove(cacheFileFullPath)


	return data

#==============================================================================

def _Cache_Add( url, data ):
	cacheKey = _Cache_CreateKey( url )
	cacheFileFullPath = os.path.join( gCacheDir, cacheKey )
	f = file(cacheFileFullPath, "w")
	f.write(data)
	f.close()

#==============================================================================

def _Cache_CreateKey( url ):
	try:
		from hashlib import md5
		return md5(url).hexdigest()
	except:
		import md5
		return  md5.new(url).hexdigest()

#==============================================================================

def _Cache_Trim():
	files = glob.glob( gCacheDir )
	if ( len(files) > gCacheSize ):
		oldestFile = get_oldest_file( files )
		cacheFileFullPath = os.path.join( gCacheDir, oldestFile )
        if os.path.exists(cacheFileFullPath):
            os.remove(cacheFileFullPath)

#==============================================================================

def get_oldest_file(files, _invert=False):
    """ Find and return the oldest file of input file names.
    Only one wins tie. Values based on time distance from present.
    Use of `_invert` inverts logic to make this a youngest routine,
    to be used more clearly via `get_youngest_file`.
    """
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

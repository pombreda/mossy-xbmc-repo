#/bin/python
# -*- coding: utf-8 -*-

REMOTE_DBG = False

# append pydev remote debugger
if REMOTE_DBG:
	# Make pydev debugger works for auto reload.
	# Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
	try:
		import pysrc.pydevd as pydevd
	# stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
		pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
		#pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)
		
	except ImportError:
		sys.stderr.write("Error: " +
			"You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
		sys.exit(1)

import os
import xbmcplugin
import xbmcgui
import xbmc
import re

from xbmcaddon import Addon

pluginName  = u'plugin.video.irishtv'
pluginHandle = int(sys.argv[1])
baseURL = sys.argv[0]

addon = Addon(pluginName)
language = addon.getLocalizedString

import mycgi

from loggingexception import LoggingException
from cachemanager import CacheManager

dbg = addon.getSetting("debug") == "true"
dbglevel = 3

from utils import log
from socket import setdefaulttimeout
from socket import getdefaulttimeout

import utils
import rtmp

import providerfactory

#import SimpleDownloader
#__downloader__ = SimpleDownloader.SimpleDownloader()
cache = CacheManager()


# Use masterprofile rather profile, because we are caching data that may be used by more than one user on the machine
DATA_FOLDER	  = xbmc.translatePath( os.path.join( u"special://masterprofile", u"addon_data", pluginName ) )
CACHE_FOLDER	 = os.path.join( DATA_FOLDER, u'cache' )
RESOURCE_PATH = os.path.join( sys.modules[u"__main__"].addon.getAddonInfo( u"path" ), u"resources" )
MEDIA_PATH = os.path.join( RESOURCE_PATH, u"media" )

#SUBTITLE_FILE	= os.path.join( DATA_FOLDER, 'subtitle.smi' )
#NO_SUBTITLE_FILE = os.path.join( RESOURCE_PATH, 'nosubtitles.smi' )

def get_system_platform():
	platform = u"unknown"
	if xbmc.getCondVisibility( u"system.platform.linux" ):
		platform = u"linux"
	elif xbmc.getCondVisibility( u"system.platform.xbox" ):
		platform = u"xbox"
	elif xbmc.getCondVisibility( u"system.platform.windows" ):
		platform = u"windows"
	elif xbmc.getCondVisibility( u"system.platform.osx" ):
		platform = u"osx"

	log(u"Platform: %s" % platform, xbmc.LOGDEBUG)
	return platform

__platform__	 = get_system_platform()


def ShowProviders():
	listItems = []
	providers = providerfactory.getProviderList()

	for provider in providers:
		providerName = provider.GetProviderId()
		log(u"Adding " + providerName + u" provider", xbmc.LOGDEBUG)
		newListItem = xbmcgui.ListItem( providerName )
		url = baseURL + u'?provider=' + mycgi.URLEscape(providerName)

		log(u"url: " + url, xbmc.LOGDEBUG)
		thumbnailPath = provider.GetThumbnailPath(providerName)
		log(providerName + u" thumbnail: " + thumbnailPath, xbmc.LOGDEBUG)
		newListItem.setThumbnailImage(thumbnailPath)
		listItems.append( (url,newListItem,True) )
	

	xbmcplugin.addDirectoryItems( handle=pluginHandle, items=listItems )
	xbmcplugin.endOfDirectory( handle=pluginHandle, succeeded=True )
		

#==============================================================================

def InitTimeout():
	log(u"getdefaulttimeout(): " + str(getdefaulttimeout()), xbmc.LOGDEBUG)
	environment = os.environ.get( u"OS", u"xbox" )
	if environment in [u'Linux', u'xbox']:
		try:
			timeout = int(addon.getSetting(u'socket_timeout'))
			if (timeout > 0):
				setdefaulttimeout(timeout)
		except:
			setdefaulttimeout(None)

#==============================================================================
def executeCommand():
	success = False
	if ( mycgi.EmptyQS() ):
		success = ShowProviders()
	else:
		providerName = mycgi.Param( u'provider' ).decode('utf8')

		log(u"providerName: " + providerName, xbmc.LOGDEBUG)
		if providerName <> u'':
			provider = providerfactory.getProvider(providerName)
			
			if provider is None:
				# ProviderFactory return none for providerName: %s
				logException = LoggingException(u"executeCommand", language(30000) % providerName)
				# 'Cannot proceed', Error processing provider name
				logException.process(language(30755), language(30020), xbmc.LOGERROR)
				return False
			
			provider.initialise(cache, sys.argv[0], pluginHandle)
			success = provider.ExecuteCommand(mycgi)
			log (u"executeCommand done", xbmc.LOGDEBUG)
			
		# else throw Exception


	return success
#		if ( search <> '' ):
#			error = DoSearch()
#		elif ( showId <> '' and episodeId == ''):
#			error = ShowEpisodes( showId, title )
#		elif ( category <> '' ):
#			error = ShowCategory( category, title, order, page )
#		elif ( episodeId <> '' ):
#			(episodeNumber, seriesNumber, swfPlayer) = mycgi.Params( 'episodeNumber', 'seriesNumber', 'swfPlayer' )
#			error = PlayOrDownloadEpisode( showId, int(seriesNumber), int(episodeNumber), episodeId, title, swfPlayer )
#	


if __name__ == "__main__":

		try:
			if addon.getSetting('http_cache_disable') == 'false':
				cache.SetCacheDir( CACHE_FOLDER )
	
			InitTimeout()
		
			# Each command processes a web page
			# Get the web page from the cache if it's there
			# If there is an error when processing the web page from the cache
			# we want to try again, this time getting the page from the web
			cache.setGetFromCache(True)
			success = executeCommand()			
	
			xbmc.log(u"success: %s, getGotFromCache(): %s" % (unicode(success), unicode(cache.getGotFromCache())), xbmc.LOGDEBUG)
			
			if success is not None and success == False and cache.getGotFromCache() == True:
				cache.setGetFromCache(False)
				executeCommand()
				log (u"executeCommand after", xbmc.LOGDEBUG)
				
		except:
			# Make sure the text from any script errors are logged
			import traceback
			traceback.print_exc(file=sys.stdout)
			raise


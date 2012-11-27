#/bin/python
# -*- coding: utf-8 -*-

import os
import xbmcplugin
import xbmcgui
import xbmc
import re
import geturllib
import mycgi

import providerfactory

from loggingexception import LoggingException
from geturllib import CacheHelper

from xbmc import log
from socket import setdefaulttimeout
from socket import getdefaulttimeout
from xbmcaddon import Addon

import utils
import rtmp

__PluginName__  = 'plugin.video.irishtv'
__PluginHandle__ = int(sys.argv[1])
__BaseURL__ = sys.argv[0]

__addon__ = Addon(__PluginName__)
__language__ = __addon__.getLocalizedString
#__downloader__ = SimpleDownloader.SimpleDownloader()
__cache__ = CacheHelper()


# Use masterprofile rather profile, because we are caching data that may be used by more than one user on the machine
DATA_FOLDER      = xbmc.translatePath( os.path.join( "special://masterprofile","addon_data", __PluginName__ ) )
CACHE_FOLDER     = os.path.join( DATA_FOLDER, 'cache' )
#SUBTITLE_FILE    = os.path.join( DATA_FOLDER, 'subtitle.smi' )
#NO_SUBTITLE_FILE = os.path.join( RESOURCE_PATH, 'nosubtitles.smi' )



def get_system_platform():
    platform = "unknown"
    if xbmc.getCondVisibility( "system.platform.linux" ):
        platform = "linux"
    elif xbmc.getCondVisibility( "system.platform.xbox" ):
        platform = "xbox"
    elif xbmc.getCondVisibility( "system.platform.windows" ):
        platform = "windows"
    elif xbmc.getCondVisibility( "system.platform.osx" ):
        platform = "osx"

    log("Platform: %s" % platform, xbmc.LOGDEBUG)
    return platform

__platform__     = get_system_platform()

	

def ShowProviders():
	listItems = []
	providers = providerfactory.getProviderList()

	for provider in providers:
		providerName = provider.GetProviderId()
		log("Adding " + providerName + " provider", xbmc.LOGDEBUG)
		newListItem = xbmcgui.ListItem( providerName )
		url = __BaseURL__ + '?provider=' + mycgi.URLEscape(providerName)

		log("url: " + url, xbmc.LOGDEBUG)
		thumbnailPath = utils.GetThumbnailPath(providerName)
		log(providerName + " thumbnail: " + thumbnailPath, xbmc.LOGDEBUG)
		newListItem.setThumbnailImage(thumbnailPath)
		listItems.append( (url,newListItem,True) )
	

	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )
		

#==============================================================================

def InitTimeout():
	log("getdefaulttimeout(): " + str(getdefaulttimeout()), xbmc.LOGDEBUG)
	environment = os.environ.get( "OS", "xbox" )
	if environment in ['Linux', 'xbox']:
		try:
			timeout = int(__addon__.getSetting('socket_timeout'))
			if (timeout > 0):
				setdefaulttimeout(timeout)
		except:
			setdefaulttimeout(None)




#==============================================================================
def executeCommand():
	if ( mycgi.EmptyQS() ):
		success = ShowProviders()
	else:
		providerName = mycgi.Param( 'provider' )

		log("providerName: " + str(providerName), xbmc.LOGDEBUG)
		if providerName <> '':
			provider = providerfactory.getProvider(providerName)
			
			if provider is None:
				# ProviderFactory return none for providerName: %s
				logException = LoggingException("executeCommand", __language__(30000) % providerName)
				# 'Cannot proceed', Error processing provider name
				logException.process(__language__(30755), __language__(30020), xbmc.LOGERROR)
				return False
			
			provider.initialise(__cache__, sys.argv[0], __PluginHandle__)
			success = provider.ExecuteCommand(mycgi)
		
		# else throw Exception


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


#TODO Handle exception, rather than error, for repeats
if __name__ == "__main__":

	try:
        	if __addon__.getSetting('http_cache_disable') == 'false':
			geturllib.SetCacheDir( CACHE_FOLDER )

		InitTimeout()
    
		# Each command processes a web page
		# Get the web page from the __cache__ if it's there
		# If there is an error when processing the web page from the __cache__
		# we want to try again, this time getting the page from the web
		__cache__.setCacheAttempt(True)
		success = executeCommand()			

		xbmc.log("success: %s, getGotFromCache(): %s" % (str(success), str(__cache__.getGotFromCache())), xbmc.LOGDEBUG)
		
		if not success and __cache__.getGotFromCache() == True:
			__cache__.setCacheAttempt(False)
			executeCommand()			

	except:
		# Make sure the text from any script errors are logged
		import traceback
		traceback.print_exc(file=sys.stdout)
		raise

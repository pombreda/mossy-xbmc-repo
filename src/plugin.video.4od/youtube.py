import re
import os
import xbmc
import xbmcgui
import utils
import urllib2
import contextlib

from errorhandler import ErrorCodes
from errorhandler import ErrorHandler

from geturllib import CacheHelper
from xbmc import log
__PluginName__  = 'plugin.video.4od'

from xbmcaddon import Addon

__addon__ = Addon(__PluginName__)
__language__ = __addon__.getLocalizedString

__YoutubePluginName__ = 'plugin.video.youtube'
__YoutubeAddon__ = Addon(__YoutubePluginName__)

DATA_FOLDER  		= xbmc.translatePath( os.path.join( "special://masterprofile","addon_data", __PluginName__ ) )
YOUTUBE_CHECK_FILE     	= os.path.join( DATA_FOLDER, 'YoutubeCheck' )

class YouTube:
	def __init__(self, cache, platform):
		self.cache = cache
		self.platform = platform
		self.installed = False


	def urlExists(self, url):

		xbmc.log ( 'Checking if url exists: %s' % url, xbmc.LOGDEBUG )
		try:			
			req = urllib2.Request(url)
			with contextlib.closing(urllib2.urlopen(req)) as res:
				newUrl = res.geturl()

		except ( urllib2.HTTPError ) as err:
			xbmc.log ( 'HTTPError: ' + str(err), xbmc.LOGDEBUG )
			return False
		except ( urllib2.URLError ) as err:
			xbmc.log ( 'URLError: ' + str(err), xbmc.LOGDEBUG )
			return False
		except ( Exception ) as e:
			xbmc.log ( 'Exception: ' + str(e), xbmc.LOGDEBUG )
			return False

		log('newUrl: %s' % newUrl, xbmc.LOGDEBUG)
		return True

	def checkInstalled(self):
		pluginId = __YoutubeAddon__.getAddonInfo( 'id' )

		log('pluginId: %s' % pluginId, xbmc.LOGDEBUG)
		if pluginId == 'plugin.video.4od':
			log('Youtube plugin not installed', xbmc.LOGDEBUG)
			self.installed = False
		else:
			log('Youtube plugin installed', xbmc.LOGDEBUG)
			self.installed = True

		return self.installed
	
	# Horrible kludge to get around Youtube problems
	# This is a temporary measure, strings will be hardcoded until this mess is removed.
	def showVersionMessage(self):
		dialog = xbmcgui.Dialog()
		dialog.ok('Youtube plugin has errors', 'The current version of the Youtube plugin won\'t work',  'with some 4od videos without changes', 'See here for more information: http://goo.gl/rA1CS')

	def checkVersion(self):
		log('Checking Youtube', xbmc.LOGDEBUG)

		if not self.checkInstalled():
			# Check build version, if Eden check youtube plugin version, if 3.2.0 show msg
			buildVersion = xbmc.getInfoLabel( "System.BuildVersion" )
			log("BuildVersion: %s" % buildVersion, xbmc.LOGDEBUG)

			if buildVersion.startswith("11."):
				log("buildVersion.startswith(\"11.\")", xbmc.LOGDEBUG)
				if self.urlExists('http://mirrors.xbmc.org/addons/eden/plugin.video.youtube/plugin.video.youtube-3.2.0.zip'):
					log("urlExists", xbmc.LOGDEBUG)
					self.showVersionMessage()
			return

		if os.path.exists(YOUTUBE_CHECK_FILE):
			log('Youtube check file exists', xbmc.LOGDEBUG)
			return

		log('Youtube check file does not exist', xbmc.LOGDEBUG)
		file = open(YOUTUBE_CHECK_FILE, 'w')
		file.write('')
		file.close()
		
		youtubeVersion = __YoutubeAddon__.getAddonInfo('version')

		log('youtubeVersion: %s' % youtubeVersion, xbmc.LOGDEBUG)
		if youtubeVersion == '3.2.0':
			self.showVersionMessage()

	def getYoutubeUrlFromId(self, youtubeId):
		if 'xbox' == self.platform:
		  url = "plugin://video/YouTube/?path=/root/video&action=play_video&videoid=" + youtubeId
		else:
		  url = "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=" + youtubeId

		return url

	def downloadFromYoutube(self, youtubeId):
		if 'xbox' == self.platform:
		  url = "plugin://video/YouTube/?path=/root/video&action=download&videoid=" + youtubeId
		else:
		  url = "plugin://plugin.video.youtube/?path=/root/video&action=download&videoid=" + youtubeId

		xbmc.executebuiltin('XBMC.RunPlugin(%s)' % url)

	def verifyYoutubePage(self, youtubeId, seriesTarget, episodeTarget):
		(episodePage, logLevel) = self.cache.GetURLFromCache( "http://www.youtube.com/watch?v=%s&has_verified=1&has_verified=1" % youtubeId, 40000 )

		if episodePage is None or len(episodePage) == 0:
			# Error getting episodePage from Youtube. youtube id:
			log (__language__(30900) + youtubeId, logLevel)
			return False

		(episodeCandidate, error) = utils.findString('verifyYoutubePage', 'Season %s Ep\. ([0-9]+?)' % seriesTarget, episodePage)

		# episodeCandidate: 
		log (__language__(30905) + episodeCandidate, logLevel)

		if episodeCandidate is not None and int(episodeCandidate) == episodeTarget:
			return True

		if error is not None:
			# Error verifying Youtube page
			error.process(__language__(30880), '', xbmc.LOGDEBUG)

		return False

	def videoFromPlaylist(self, playlist, seriesNumber, episodeNumber):
		# Best guess - assume that the episodes are listed in order starting with 1. Works out that way a lot of the time, but not always.
		(youtubeId, error) = utils.findString('videoFromPlaylist', 'href="/watch\?v=([^&]*?)&[^"]*?index=%s' % episodeNumber, playlist)

		if error is None:

			# Verify 
			if self.verifyYoutubePage(youtubeId, seriesNumber, episodeNumber):
				return (youtubeId, None)

	
		# Try each index in turn	
		youtubeIdList = re.findall( 'href="/watch\?v=([^&]*?)&[^"]*?index=[0-9]*?', playlist, re.DOTALL | re.IGNORECASE )

		for youtubeId in youtubeIdList:
			if self.verifyYoutubePage(youtubeId, seriesNumber, episodeNumber):
				return (youtubeId, None)

		# Season %i, Episode %i
		error = ErrorHandler('videoFromPlaylist', ErrorCodes.UNABLE_TO_FIND_YOUTUBE_ID, __language__(30935) % (seriesNumber, episodeNumber))

		log ('videoFromPlaylist: youtubeId, error: %s, %s' % (str(youtubeId), str(error)))
		return (None, error)	
	

	def getYoutubeId(self, title, defaultFilename):
		# Searching Youtube...
		log (__language__(30910), xbmc.LOGWARNING)

		youtubeId = None
		title = title.replace( '-', '' )

		match = re.search('s([0-9][0-9])e([0-9][0-9])', defaultFilename)
		if match:
			seriesNumber = int(match.group(1))
			episodeNumber = int(match.group(2))

			# getYoutubeUrl seriesNumber: 
			# getYoutubeUrl episodeNumber: 	 
			log (__language__(30915) + str(seriesNumber), xbmc.LOGDEBUG)
			log (__language__(30920) + str(episodeNumber), xbmc.LOGDEBUG)

			(tubeShow, logLevel) = self.cache.GetURLFromCache( "http://www.youtube.com/show/%s" % title, 600 )
		
			if tubeShow is None or tubeShow == '':
				error = ErrorHandler('getYoutubeId', ErrorCodes.ERROR_GETTING_YOUTUBE_SHOW, '')
				return ( None, error )

			(playlistAppendage, error) = utils.findString('getYoutubeId', 'href="([^"]*?)">\s+Season %s Episodes' % seriesNumber, tubeShow)

			if error is None:
				(tubeSeasonPlaylist, logLevel) = self.cache.GetURLFromCache( "http://www.youtube.com%s" % playlistAppendage, 600 )

				if tubeSeasonPlaylist is None or tubeSeasonPlaylist == '':
					error = ErrorHandler('getYoutubeId', ErrorCodes.ERROR_GETTING_YOUTUBE_SEASON, '')
					return ( None, error )

				log ('seriesNumber, episodeNumber: %s, %s' % (str(seriesNumber), str(episodeNumber)), xbmc.LOGDEBUG)

				(youtubeId, error) = self.videoFromPlaylist(tubeSeasonPlaylist, seriesNumber, episodeNumber)
				log ('youtubeId, error: %s, %s' % (str(youtubeId), str(error)))
				

		else:
			# defaultFilename: 
			error = ErrorHandler('getYoutubeId', ErrorCodes.CANNOT_DETERMINE_SHOW_NUMBERS, __language__(30925) + defaultFilename )


		return (youtubeId, error)



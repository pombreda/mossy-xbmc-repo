#/bin/p__youtube__hon
# -*- coding: utf-8 -*-

# Remove "see previous" from Youtube errors
import os
import xbmcplugin
import xbmcgui
import xbmc
import re
import geturllib
import fourOD_token_decoder
import mycgi

from errorhandler import ErrorCodes
from errorhandler import ErrorHandler
from episodelist import EpisodeList

from geturllib import CacheHelper

from xbmc import log
from socket import setdefaulttimeout
from socket import getdefaulttimeout
from urlparse import urlunparse
from xbmcaddon import Addon

import youtube
import utils
import rtmp

__PluginName__  = 'plugin.video.4od'
__PluginHandle__ = int(sys.argv[1])
__BaseURL__ = sys.argv[0]

__addon__ = Addon(__PluginName__)
__language__ = __addon__.getLocalizedString

RESOURCE_PATH = os.path.join( __addon__.getAddonInfo( "path" ), "resources" )
MEDIA_PATH = os.path.join( RESOURCE_PATH, "media" )

# Use masterprofile rather profile, because we are caching data that may be used by more than one user on the machine
DATA_FOLDER      = xbmc.translatePath( os.path.join( "special://masterprofile","addon_data", __PluginName__ ) )
CACHE_FOLDER     = os.path.join( DATA_FOLDER, '__cache__' )
SUBTITLE_FILE    = os.path.join( DATA_FOLDER, 'subtitle.smi' )
NO_SUBTITLE_FILE = os.path.join( RESOURCE_PATH, 'nosubtitles.smi' )


__cache__ = CacheHelper()

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

__youtube__ = youtube.YouTube(__cache__, __platform__)


#==============================================================================
# ShowCategoriese[p
#
# List the programme categories, retaining the 4oD order
#==============================================================================

def ShowCategories():
	(html, logLevel) = __cache__.GetURLFromCache("http://www.channel4.com/programmes/tags/4od", 20000)

	if html is None or html == '':
		error = ErrorHandler('ShowCategories', ErrorCodes.ERROR_GETTING_CATEGORY_PAGE, __language__(30800)) 
		# 'Cannot show categories'
		error.process(__language__(30765), '', logLevel)
		return error

	pattern = '<ol class="display-cats">(.*?)</div>'
	displayCategories = re.findall( pattern, html, re.DOTALL | re.IGNORECASE )

	if len(displayCategories) == 0:
		messageLog = cantFindPatternLog(pattern, html) 

		error = ErrorHandler(method, ErrorCodes.CANT_FIND_PATTERN_IN_STRING, messageLog)
 		# 'Cannot show categories'
		error.process(__language__(30765), '', logLevel)
		return error
		
	pattern = '<a href="/programmes/tags/(.*?)/4od">(.*?)</a>'
	categories = re.findall( pattern, displayCategories[0], re.DOTALL | re.IGNORECASE )
	
	if len(categories) == 0:
		messageLog = cantFindPatternLog(pattern, html) 

		error = ErrorHandler('ShowCategories', ErrorCodes.ERROR_GETTING_CATEGORY_PAGE, messageLog)
		# 'Cannot show categories'
		error.process(__language__(30765), '', logLevel)
		return error
		
	listItems = []
	# Start with a Search entry	'Search'
	newListItem = xbmcgui.ListItem( __language__(30500) )
	url = __BaseURL__ + '?search=1'
	listItems.append( (url,newListItem,True) )
	for categoryInfo in categories:
		label = utils.remove_extra_spaces(utils.remove_html_tags(categoryInfo[1]))
		newListItem = xbmcgui.ListItem( label=label )
		url = __BaseURL__ + '?category=' + mycgi.URLEscape(categoryInfo[0]) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape('/title') + '&page=' + mycgi.URLEscape('1')
		listItems.append( (url,newListItem,True) )
	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )
		
	return None


#==============================================================================
# GetThumbnailPath
#
# Convert local file path to URI to workaround delay in showing 
# thumbnails in Banner view
#==============================================================================

def GetThumbnailPath(thumbnail):
	if __platform__ == "linux":
		return urlunparse(('file', '/', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))

#	return os.path.join(MEDIA_PATH, thumbnail + '.jpg')
	return urlunparse(('file', '', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))
#

#==============================================================================
# AddExtraLinks
#
# Add links to 'Most Popular'. 'Latest', etc to programme listings
#==============================================================================

def AddExtraLinks(category, label, order, listItems):
	(html, logLevel) = __cache__.GetURLFromCache( "http://www.channel4.com/programmes/tags/%s/4od%s" % (category, order), 40000 ) # ~12 hrs

	if html is None or html == '':
		error = ErrorHandler('AddExtraLinks', ErrorCodes.ERROR_GETTING_PROGRAMME_PAGE, __language__(30800))
		return error


	extraInfos = re.findall( '<a href="/programmes/tags/%s/4od(.*?)">(.*?)</a>' % (category) , html, re.DOTALL | re.IGNORECASE )


	for extraInfo in extraInfos:
		if extraInfo[1] == 'Show More':
			continue

		newOrder = extraInfo[0]

		thumbnail = extraInfo[0]
		if thumbnail == '':
			thumbnail = 'latest'
		else:
			thumbnail = utils.remove_leading_slash(thumbnail)

		thumbnailPath = GetThumbnailPath(thumbnail)
		newLabel = ' [' + extraInfo[1] + ' ' + utils.remove_extra_spaces(utils.remove_brackets(label))+ ']'
		newListItem = xbmcgui.ListItem( label=newLabel )
		newListItem.setThumbnailImage(thumbnailPath)

		url = __BaseURL__ + '?category=' + mycgi.URLEscape(category) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape(newOrder) + '&page=' + mycgi.URLEscape('1')
		listItems.append( (url,newListItem,True) )

	return None

#==============================================================================
# AddPageLink
#
# Add Next/Previous Page links to programme listings
#==============================================================================

def AddPageLink(category, order, previous, page, listItems):
	thumbnail = 'next'
	arrows = '>>'
	if previous == True:
		thumbnail = 'previous'
		arrows = '<<'

	thumbnailPath = GetThumbnailPath(thumbnail)
	# E.g. [Page 2] >>
	label = '[' + __language__(30510) + ' ' + page + '] ' + arrows

	newListItem = xbmcgui.ListItem( label=label )
	newListItem.setThumbnailImage(thumbnailPath)

	url = __BaseURL__ + '?category=' + mycgi.URLEscape(category) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape(order) + '&page=' + mycgi.URLEscape(page)
	listItems.append( (url,newListItem,True) )


#==============================================================================
# AddPageToListItems
#
# Add the shows from a particular page to the listItem array
#==============================================================================

def AddPageToListItems( category, label, order, page, listItems ):
	(html, logLevel) = __cache__.GetURLFromCache( "http://www.channel4.com/programmes/tags/%s/4od%s/brand-list/page-%s" % (category, order, page), 40000 ) # ~12 hrs

	if html is None or html == '':
		error = ErrorHandler('AddPageToListItems', ErrorCodes.ERROR_GETTING_PROGRAMME_PAGE, __language__(30800))
		return error

	showsInfo = re.findall( '<li.*?<a class=".*?" href="/programmes/(.*?)/4od".*?<img src="(.*?)".*?<p class="title">(.*?)</p>.*?<p class="synopsis">(.*?)</p>', html, re.DOTALL | re.IGNORECASE )

	for showInfo in showsInfo:
		showId = showInfo[0]
		thumbnail = "http://www.channel4.com" + showInfo[1]
		progTitle = showInfo[2]
		progTitle = progTitle.replace( '&amp;', '&' )
		synopsis = showInfo[3].strip()
		synopsis = synopsis.replace( '&amp;', '&' )
		synopsis = synopsis.replace( '&pound;', '£' )
		
		newListItem = xbmcgui.ListItem( progTitle )
		newListItem.setThumbnailImage(thumbnail)
		newListItem.setInfo('video', {'Title': progTitle, 'Plot': synopsis, 'PlotOutline': synopsis})
		url = __BaseURL__ + '?category=' + category + '&show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(progTitle)
		listItems.append( (url,newListItem,True) )

	(nextUrl, error) = utils.findString('AddPageToListItems', '<ol class="promo-container" data-nexturl="(.*?)"', html)
	if error is not None:
		# 'Error finding next page', 'Cannot determine if this is the last page or not'
		error.process(__language__(30720), __language__(30725), '', logLevel)
		nextUrl = 'endofresults'

	return nextUrl


#==============================================================================


def ShowCategory( category, label, order, page ):
	listItems = []

	pageInt = int(page)
	if pageInt == 1:
		error = AddExtraLinks(category, label, order, listItems)
		if error is not None:
			# 'Cannot show Most Popular/A-Z/Latest', 'Error processing web page'
			error.process(__language__(30775), __language__(30780), xbmc.LOGWARNING)


	paging = __addon__.getSetting( 'paging' )

	if (paging == 'true'):
		if pageInt > 1:
			AddPageLink(category, order, True, str(pageInt - 1), listItems)

		nextUrl = AddPageToListItems( category, label, order, page, listItems )
		if isinstance(nextUrl, ErrorHandler):
			error = nextUrl
			# 'Cannot show category', 'Error processing web page'
			error.process(__language__(30785), __language__(30780), xbmc.LOGERROR)
			return		

		if (nextUrl.lower() <> 'endofresults'):
			nextPage = str(pageInt + 1)
			AddPageLink(category, order, False, nextPage, listItems)

	else:
		nextUrl = ''
		while len(listItems) < 500 and nextUrl.lower() <> 'endofresults':
			nextUrl = AddPageToListItems( category, label, order, page, listItems )
			if isinstance(nextUrl, ErrorHandler):
				error = nextUrl
				# 'Cannot show category', 'Error processing web page'
				error.process(__language__(30785), __language__(30780), xbmc.LOGERROR)
				return		

			pageInt = pageInt + 1
			page = str(pageInt)
			

	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='tvshows')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )


#==============================================================================

def ShowEpisodes( showId, showTitle ):
	episodeList = EpisodeList(__BaseURL__, __cache__)

	error = episodeList.initialise(showId, showTitle)
	if error is not None:
		# "Error parsing html", "Cannot list episodes."
		error.process(__language__(30735), __language__(30740), xbmc.LOGERROR)
		return

	listItems = episodeList.createListItems(mycgi)

	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='episodes')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )

#==============================================================================

def SetSubtitles(episodeId, filename = None):
	(subtitle, logLevel) = __cache__.GetURLFromCache( "http://ais.channel4.com/subtitles/%s" % episodeId, 40000 )
	
	log('Subtitle code: ' + str(geturllib.GetLastCode()), xbmc.LOGDEBUG )
	log('Subtitle filename: ' + str(filename), xbmc.LOGDEBUG)

	if subtitle is not None:
		log('Subtitle file length: ' + str(len(subtitle)), xbmc.LOGDEBUG)

	log('geturllib.GetLastCode(): ' + str(geturllib.GetLastCode()), xbmc.LOGDEBUG)

	if (geturllib.GetLastCode() == 404 or subtitle is None or len(subtitle) == 0):
		log('No subtitles available', xbmc.LOGWARNING )
		subtitleFile = NO_SUBTITLE_FILE
	else:
		if filename is None:
			subtitleFile = SUBTITLE_FILE
		else:
			subtitleFile = filename

		quotedSyncMatch = re.compile('<Sync Start="(.*?)">', re.IGNORECASE)
		subtitle = quotedSyncMatch.sub('<Sync Start=\g<1>>', subtitle)
		subtitle = subtitle.replace( '&quot;', '"')
		subtitle = subtitle.replace( '&apos;', "'")
		subtitle = subtitle.replace( '&amp;', '&' )
		subtitle = subtitle.replace( '&pound;', '£' )
		subtitle = subtitle.replace( '&lt;', '<' )
		subtitle = subtitle.replace( '&gt;', '>' )

		filesub=open(subtitleFile, 'w')
		filesub.write(subtitle)
		filesub.close()

  	return subtitleFile

#==============================================================================

def GetDownloadSettings(defaultFilename):
	
	# Ensure rtmpdump has been located
	rtmpdumpPath = __addon__.getSetting('rtmpdump_path')
	if ( rtmpdumpPath is '' ):
		dialog = xbmcgui.Dialog()
		# Download Error - You have not located your rtmpdump executable...
		dialog.ok(__language__(30560),__language__(30570),'','')
		__addon__.openSettings(sys.argv[ 0 ])

		rtmpdumpPath = __addon__.getSetting('rtmpdump_path')
		if ( rtmpdumpPath is '' ):
			return
		
	# Ensure default download folder is defined
	downloadFolder = __addon__.getSetting('download_folder')
	if downloadFolder is '':
		d = xbmcgui.Dialog()
		# Download Error - You have not set the default download folder.\n Please update the addon settings and try again.','','')
		d.ok(__language__(30560),__language__(30580),'','')
		__addon__.openSettings(sys.argv[ 0 ])

		downloadFolder = __addon__.getSetting('download_folder')
		if downloadFolder is '':
			return
		
	if ( __addon__.getSetting('ask_filename') == 'true' ):
		# Save programme as...
		kb = xbmc.Keyboard( defaultFilename, __language__(30590))
		kb.doModal()
		if (kb.isConfirmed()):
			filename = kb.getText()
		else:
			return
	else:
		filename = defaultFilename
	
	if ( filename.endswith('.flv') == False ): 
		filename = filename + '.flv'
	
	if ( __addon__.getSetting('ask_folder') == 'true' ):
		dialog = xbmcgui.Dialog()
		# Save to folder...
		downloadFolder = dialog.browse(  3, __language__(30600), 'files', '', False, False, downloadFolder )
		if ( downloadFolder == '' ):
			return

	return (rtmpdumpPath, downloadFolder, filename)

#==============================================================================
# Play
#
#
#==============================================================================

def Play(playURL, showId, episodeId, title):
	log ('Play showId: ' + showId)
	log ('Play episodeId: ' + episodeId)
	log ('Play titleId: ' + title)
	log ('Play url: ' + playURL)

	episodeList = EpisodeList(__BaseURL__, __cache__)
	error = episodeList.initialise(showId, title)
	if error is None:
		listItem = episodeList.createNowPlayingListItem(episodeId)
	else:
		# "Error parsing html", "Cannot add show to \"Now Playing\"
		error.process(__language__(30735), __language__(30745), xbmc.LOGWARNING)
	
		listItem = xbmcgui.ListItem(title)
		listItem.setInfo('video', {'Title': title})

	play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
	play.clear()
	play.add(playURL, listItem)

	xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)

	subtitles = __addon__.getSetting( 'subtitles' )

	if (subtitles == 'true'):
		subtitleFile = SetSubtitles(episodeId)
		xbmc.Player().setSubtitles(subtitleFile)

#==============================================================================
def Download(rtmpvar, youtubeId, episodeId, defaultFilename):
	if youtubeId is None:
		DownloadRTMP(rtmpvar, episodeId, defaultFilename)
	else:
		__youtube__.downloadFromYoutube(youtubeId)

def DownloadRTMP(rtmpvar, episodeId, defaultFilename):
	(rtmpdumpPath, downloadFolder, filename) = GetDownloadSettings(defaultFilename)
	
	savePath = os.path.join( downloadFolder, filename )

        subtitles = __addon__.getSetting( 'subtitles' )

        if (subtitles == 'true'):
                log ("Getting subtitles")
                # Replace '.flv' or other 3 character extension with '.smi'
                SetSubtitles(episodeId, savePath[0:-4] + '.smi')

	rtmpvar.setDownloadDetails(rtmpdumpPath, savePath)

	parameters = rtmpvar.getParameters()

	from subprocess import Popen, PIPE, STDOUT
		
	# Starting download
	log ("Starting download: " + rtmpdumpPath + " " + str(parameters))
	xbmc.executebuiltin('XBMC.Notification(4oD %s, %s)' % ( __language__(30610), filename))

	log('"%s" %s' % (rtmpdumpPath, parameters))
	if get_system_platform() == 'windows':
		p = Popen( parameters, executable=rtmpdumpPath, shell=True, stdout=PIPE, stderr=PIPE )
	else:
		cmdline = '"%s" %s' % (rtmpdumpPath, parameters)
		p = Popen( cmdline, shell=True, stdout=PIPE, stderr=PIPE )

	log ("rtmpdump has started executing", xbmc.LOGDEBUG)
	(stdout, stderr) = p.communicate()
	log ("rtmpdump has stopped executing", xbmc.LOGDEBUG)

	if 'Download complete' in stderr:
		# Download Finished!
		log ('stdout: ' + str(stdout), xbmc.LOGDEBUG)
		log ('stderr: ' + str(stderr), xbmc.LOGDEBUG)
		log ("Download Finished!")
		xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( __language__(30620), filename))
	else:
		# Download Failed!
		log ('stdout: ' + str(stdout), xbmc.LOGERROR)
		log ('stderr: ' + str(stderr), xbmc.LOGERROR)
		log ("Download Failed!")
		xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( "Download Failed! See log for details", filename))
		

#==============================================================================

def GetAuthentication(uriData):
	(token, error) = utils.findString('GetAuthentication', '<token>(.*?)</token>', uriData)
	if error is not None:
		return error
		
	(cdn, error) = utils.findString('GetAuthentication', '<cdn>(.*?)</cdn>', uriData)
	if error is not None:
		return error
	
	log("cdn: %s" % cdn, xbmc.LOGDEBUG)
	log("token: %s" % token, xbmc.LOGDEBUG)
	decodedToken = fourOD_token_decoder.Decode4odToken(token)

	if ( cdn ==  "ll" ):
		(e, error) = utils.findString('GetAuthentication', '<e>(.*?)</e>', uriData)
		log("e: %s" % e, xbmc.LOGDEBUG)
		if error is not None:
			return error
	
		log("e: %s" % e, xbmc.LOGDEBUG)
		ip = re.search( '<ip>(.*?)</ip>', uriData, re.DOTALL | re.IGNORECASE )
		if (ip):
			log("ip: %s" % ip, xbmc.LOGDEBUG)
			auth = "e=%s&ip=%s&h=%s" % (e,ip.group(1),decodedToken)
		else:
			auth = "e=%s&h=%s" % (e,decodedToken)
	else:
		return ErrorHandler('GetStreamInfo', ErrorCodes.WRONG_CONTENT_DELIVERY_NETWORK, __language__(30950) )
#		(fingerprint, error) = utils.findString('GetAuthentication', '<fingerprint>(.*?)</fingerprint>', uriData)
#		if error is not None:
#			return error
#	
#		(slist, error) = utils.findString('GetAuthentication', '<slist>(.*?)</slist>', uriData)
#		if error is not None:
#			return error
#	
#		auth = "auth=%s&aifp=%s&slist=%s" % (decodedToken,fingerprint,slist)

	log("auth: %s" % auth, xbmc.LOGDEBUG)

	return auth
	

#==============================================================================

def GetStreamInfo(episodeId):

	maxAttempts = 10
	for attemptNumber in range(0, maxAttempts):
		(xml, logLevel) = __cache__.GetURLFromCache( "http://ais.channel4.com/asset/%s" % episodeId, 0 )

		if xml is None or xml == '':
			error = ErrorHandler('GetStreamInfo', ErrorCodes.ERROR_GETTING_STREAM_INFO_XML, __language__(30800))
			return error

		(uriData, error) = utils.findString('GetStreamInfo', '<uriData>(.*?)</uriData>', xml)
		if error is not None:
			return error
		
		(streamURI, error) = utils.findString('GetStreamInfo', '<streamUri>(.*?)</streamUri>', uriData)
		if error is not None:
			return error
		

		# If HTTP Dynamic Streaming is used for this show then there will be no mp4 file,
		# and decoding the token will fail, therefore we abort before
		# parsing authentication info if there is no mp4 file.
		if 'mp4:' not in streamURI.lower():
			# Unable to find MP4 video file to play.
			# No MP4 found, probably HTTP Dynamic Streaming. Stream URI - %s
			error = ErrorHandler('GetStreamInfo', ErrorCodes.UNABLE_TO_FIND_MP4, __language__(30815) % streamURI)
			return error

		auth =  GetAuthentication(uriData)
	
		if isinstance(auth, ErrorHandler):
			error = auth
			# If we didn't get the cdn we're looking for then try again
			# Error getting correct cdn, trying again
			if error.errorCode == ErrorCodes.WRONG_CONTENT_DELIVERY_NETWORK:
				error.process(__language__(30955), '', xbmc.LOGDEBUG)
				continue

			return auth

		break

	if isinstance(auth, ErrorHandler):
		# Will only get here if there after several failed attempts at
		return auth

	return (streamURI, auth)

#==============================================================================

def GetAction(title):
	actionSetting = __addon__.getSetting( 'select_action' )
	log ("action: " + actionSetting, xbmc.LOGDEBUG)

	# Ask
	if ( actionSetting == __language__(30120) ):
		dialog = xbmcgui.Dialog()
		# Do you want to play or download?	
		##listoptions = [__language__(30130), __language__(30140)]
		##action = dialog.select(title, listoptions) # 1=Play; 0=Download

		action = dialog.yesno(title, __language__(30530), '', '', __language__(30140),  __language__(30130)) # 1=Play; 0=Download
	# Download
	elif ( actionSetting == __language__(30140) ):
		action = 0
	else:
		action = 1

	return action

#==============================================================================

def InitialiseRTMP(episodeId, swfPlayer):
	log('InitialiseRTMP: episodeId: %s' % episodeId, xbmc.LOGDEBUG)

	# Get the stream info
	details = GetStreamInfo(episodeId)

	if isinstance(details, ErrorHandler):
		return details
		
	(streamUri, auth) = details

	rtmpvar = rtmp.RTMP()
	error = rtmpvar.setDetailsFromURI(streamUri, auth, swfPlayer)

	if error is not None:
		return error

	return rtmpvar

#==============================================================================
def getYoutubeUrl(showId, defaultFilename, logLevel):
	(youtubeId, errorYoutube) = __youtube__.getYoutubeId(showId, defaultFilename)

	log ('PlayOrDownloadEpisode: youtubeId, error: %s, %s' % (str(youtubeId), str(errorYoutube)))

	if errorYoutube is None:
		playUrl = __youtube__.getYoutubeUrlFromId(youtubeId)
	else:
		# Error streaming video from Youtube, It's possible that this programme is not available from 4od on Youtube (e.g. all US shows) or is not avilable on Youtube yet
		errorYoutube.process(__language__(30850), __language__(30855), logLevel)

	return (youtubeId, playUrl, errorYoutube)


def getRTMPUrl(showId, episodeId, defaultFilename, swfPlayer, dialog):
	playUrl = None
	youtubeId = None

	rtmpvar = InitialiseRTMP(episodeId, swfPlayer)
	if isinstance(rtmpvar, ErrorHandler):
		if dialog.iscanceled():
			return

		# 'Looking for video on Youtube'
		if __addon__.getSetting( 'youtube_enable' ):
			# Check if youtube installed, version
			# If version is "3.2.0" show msg: Go here to get working version
			# If not installed wait until after play/download, do same check and msg show same msg.
			__youtube__.checkVersion()
			dialog.update(50, __language__(30890))
			(youtubeId, playUrl, errorYoutube) = getYoutubeUrl(showId, defaultFilename, xbmc.LOGDEBUG)

		# Indicates that either youtube is not enabled, or we failed to get the youtube url
		if playUrl is None:
			# 'Cannot proceed'
			message = __language__(30755)

			errorRtmp = rtmpvar

			if __addon__.getSetting( 'youtube_enable' ):
				message = message + ' ' + __language__(30845)
				errorRtmp.messageSummary = errorRtmp.messageSummary + ' ' + __language__(30940)

				if errorYoutube is not None:
					errorRtmp.messageSummary = errorRtmp.messageSummary + ' - ' + errorYoutube.messageSummary

			# 'Error parsing stream info', 'Cannot proceed (also unable to stream video from Youtube, see previous log msg)'
			errorRtmp.process(__language__(30750), message, xbmc.LOGERROR)
		else:
			log("playUrl is not None", xbmc.LOGERROR)
			# Log rtmp error
			# 'Cannot proceed'
			message = __language__(30755)

			errorRtmp = rtmpvar

			log("%s, %s" % (errorRtmp.messageSummary, errorRtmp.messageLog), xbmc.LOGERROR)
			# 'Error parsing stream info', 'Cannot proceed (also unable to stream video from Youtube, see previous log msg)'
			errorRtmp.process(__language__(30750), message, xbmc.LOGDEBUG)

	
	else:
		playUrl = rtmpvar.getPlayUrl()	

	return (youtubeId, playUrl, rtmpvar)

def PlayOrDownloadEpisode( showId, episodeId, title, defaultFilename, swfPlayer ):
	log ('PlayOrDownloadEpisode showId: ' + showId, xbmc.LOGDEBUG)
	log ('PlayOrDownloadEpisode episodeId: ' + episodeId, xbmc.LOGDEBUG)
	log ('PlayOrDownloadEpisode title: ' + title, xbmc.LOGDEBUG)

	dialog = xbmcgui.DialogProgress()
	dialog.create('4od', '')
#	if __addon__.getSetting( 'youtube_forced' ):
#		# 'Looking for video on Youtube'
#		dialog.update(0,  __language__(30890))
#		(youtubeId, playUrl, errorYoutube) = getYoutubeUrl(showId.lower(), defaultFilename, xbmc.LOGERROR)
#	else:

	# 'Looking for video on 4od'
	dialog.update(0,  __language__(30885))
	(youtubeId, playUrl, rtmpvar) = getRTMPUrl(showId.lower(), episodeId, defaultFilename, swfPlayer, dialog)

	if dialog.iscanceled():
		return

	dialog.close()

	action = GetAction(title)

#	installedBefore = __youtube__.checkInstalled()

	if ( action == 1 ):
		# Play
		Play(playUrl, showId, episodeId, title)
	
	else:
		if ( action == 0 ):
			# Download
			if youtubeId is None:
				Download(rtmpvar, youtubeId, episodeId, defaultFilename)
			else:
				__youtube__.downloadFromYoutube(youtubeId)

#	if not installedBefore:
#		log('Not installed before', xbmc.LOGDEBUG)
#		xbmc.executebuiltin('UpdateLocalAddons')
#		installedAfter = __youtube__.checkInstalled()
#
#		if installedAfter:
#			log('Installed before', xbmc.LOGDEBUG)
#			__youtube__.checkVersion()
#
#	log('After Play/Download', xbmc.LOGDEBUG)
	return

#==============================================================================

def DoSearch():
	# Search
	kb = xbmc.Keyboard( "", __language__(30500) )
	kb.doModal()
	if ( kb.isConfirmed() == False ): return
	query = kb.getText()

	return DoSearchQuery( query )

#==============================================================================

def DoSearchQuery( query ):
	(data, logLevel) = __cache__.GetURLFromCache( "http://www.channel4.com/search/predictive/?q=%s" % mycgi.URLEscape(query), 10000 )
	if data is None or data == '':
		# Error getting search web page
		# See previous error
		error = ErrorHandler('DoSearchQuery', ErrorCodes.ERROR_GETTING_SEARCH_WEB_PAGE, __language__(30800))
		return error

	infos = re.findall( '{"imgUrl":"(.*?)".*?"value": "(.*?)".*?"siteUrl":"(.*?)","fourOnDemand":"true"}', data, re.DOTALL | re.IGNORECASE )
	listItems = []
	for info in infos:
		image = info[0]
		title = info[1]
		progUrl  = info[2]
		
		title = title.replace( '&amp;', '&' )
		title = title.replace( '&pound;', '£' )
		title = title.replace( '&quot;', "'" )
		
		image = "http://www.channel4.com" + image

		(showId, error) = utils.findString('DoSearchQuery', 'programmes/(.*?)/4od', progUrl)
		if error is not None:
			# Cannot find show id
			error.process(__language__(30760),'',xbmc.LOGWARNING)
			continue

		newListItem = xbmcgui.ListItem( title )
		newListItem.setThumbnailImage(image)
		url = __BaseURL__ + '?show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(title)
		listItems.append( (url,newListItem,True) )


	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='tvshows')
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
	error = None
	if ( mycgi.EmptyQS() ):
		error = ShowCategories()
	else:
		(category, showId, episodeId, title, search, swfPlayer, order, page) = mycgi.Params( 'category', 'show', 'ep', 'title', 'search', 'swfPlayer', 'order', 'page' )

		if ( search <> '' ):
			error = DoSearch()
		elif ( showId <> '' and episodeId == ''):
			error = ShowEpisodes( showId, title )
		elif ( category <> '' ):
			error = ShowCategory( category, title, order, page )
		elif ( episodeId <> '' ):
			error = PlayOrDownloadEpisode( showId, episodeId, title, mycgi.Param('fn'), swfPlayer )
	
	return error


if __name__ == "__main__":

	try:
        	if __addon__.getSetting('http___cache___disable_adv') == 'false':
			geturllib.SetCacheDir( CACHE_FOLDER )

		InitTimeout()
    
		# Each command processes a web page
		# Get the web page from the __cache__ if it's there
		# If there is an error when processing the web page from the __cache__
		# we want to try again, this time getting the page from the web
		__cache__.setCacheAttempt(True)
		error = executeCommand()			

		if error is not None and __cache__.getCacheAttempt() == True:
			__cache__.setCacheAttempt(False)
			error = executeCommand()			

	except:
		# Make sure the text from any script errors are logged
		import traceback
		traceback.print_exc(file=sys.stdout)
		raise

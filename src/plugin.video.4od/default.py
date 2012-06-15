#/bin/python
# -*- coding: utf-8 -*-

import os
import xbmcplugin
import xbmcgui
import xbmc
import re
import geturllib
import fourOD_token_decoder
import mycgi
import urllib2

from xbmc import log
#from socket import setdefaulttimeout
from urlparse import urlunparse
from xbmcaddon import Addon

__PluginName__  = 'plugin.video.4od'
__PluginHandle__ = int(sys.argv[1])
__BaseURL__ = sys.argv[0]

__addon__ = Addon(__PluginName__)
__language__ = __addon__.getLocalizedString

# Only used if we fail to parse the URL from the website
__SwfPlayerDefault__ = 'http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer_am2.1.swf'

RESOURCE_PATH = os.path.join( __addon__.getAddonInfo( "path" ), "resources" )
MEDIA_PATH = os.path.join( RESOURCE_PATH, "media" )

# Use masterprofile rather profile, because we are caching data that may be used by more than one user on the machine
DATA_FOLDER      = xbmc.translatePath( os.path.join( "special://masterprofile","addon_data", __PluginName__ ) )
CACHE_FOLDER     = os.path.join( DATA_FOLDER, 'cache' )
SUBTITLE_FILE    = os.path.join( DATA_FOLDER, 'subtitle.smi' )
NO_SUBTITLE_FILE = os.path.join( RESOURCE_PATH, 'nosubtitles.smi' )

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


class ErrorHandler:

	def __init__(self, method, messageDetail, messageLog = None, messageHeading = 'Error'):

		self.method 		= method
		self.messageDetail 	= messageDetail
		self.messageLog 	= messageLog
		self.messageHeading 	= messageHeading


	def process(self, messageHeading = None, messageOverview = '', level = xbmc.LOGDEBUG):
		if messageHeading is not None:
			self.messageHeading = messageHeading

		if len(messageOverview) > 0:
			self.messageOverview = messageOverview + ' - ' + self.messageDetail 
		else:
			self.messageOverview = self.messageDetail


		if self.messageLog is not None:
			log('In %s: %s: %s\n%s' % (self.method, self.messageHeading, self.messageOverview, self.messageLog), level)
		else:
			log('In %s: %s: %s' (self.method, self.messageHeading, self.messageOverview), level)

		if level == xbmc.LOGERROR:
			dialog = xbmcgui.Dialog()
			dialog.ok(self.messageHeading, self.messageDetail + '\nSee log for details','','')
		elif level == xbmc.LOGWARNING:
			# See log for details
			xbmc.executebuiltin('XBMC.Notification(4oD %s, %s)' % (self.messageHeading, __language__(30700)))


def findString(method, pattern, string, flags = (re.DOTALL | re.IGNORECASE)):
	match = re.search( pattern, string, flags )
	if match is not None:
		return (match.group(1), None)

	# Limit logging of string to 100 chars
	limit = 1000
	# Can't find pattern in string
	messageDetails = __language__(30705)
	messageLog = "\nPattern - \n%s\n\nString - \n%s\n\n" % (pattern, string[0:limit])


	return (None, ErrorHandler(method, messageDetails, messageLog))


class RTMP:
	def __init__(self):
		self.url = None
		self.auth = None
                self.app = None
                self.playPath = None
                self.swfPlayer = None

		self.rtmpdumpPath = None
                self.savePath = None


	def setDetailsFromURI(self, streamURI, auth, swfPlayer):
		log('setDetailsFromURI streamURI: ' + streamURI, xbmc.LOGDEBUG)
		log('setDetailsFromURI swfPlayer: ' + swfPlayer, xbmc.LOGDEBUG)

		(self.url, error) = findString('setDetailsFromURI', '(.*?)mp4:', streamURI)
		if error is not None:
			return error

		self.url = self.url.replace( '.com/', '.com:1935/' )
		#self.url = self.url + "?ovpfv=1.1&" + auth

		(self.app, error) = findString('setDetailsFromURI', '.com/(.*?)mp4:', streamURI)
		if error is not None:
			return error

		self.app = self.app + "?ovpfv=1.1&" + auth

		(self.playPath, error) = findString('setDetailsFromURI', '(mp4:.*)', streamURI)
		if error is not None:
			return error

		self.playPath = self.playPath + '?' + auth

		self.swfPlayer = swfPlayer
		self.auth = auth

		log ("setDetailsFromURI url: " + self.url, xbmc.LOGDEBUG)
		log ("setDetailsFromURI app: " + self.app, xbmc.LOGDEBUG)
		log ("setDetailsFromURI playPath: " + self.playPath, xbmc.LOGDEBUG)
		log ("setDetailsFromURI auth: " + self.auth, xbmc.LOGDEBUG)

		return None

	def setDownloadDetails(self, rtmpdumpPath, savePath):
                self.rtmpdumpPath = rtmpdumpPath
                self.savePath = savePath
	
		log ("setDownloadDetails rtmpdumpPath: " + self.rtmpdumpPath, xbmc.LOGDEBUG)
		log ("setDownloadDetails savePath: " + self.savePath, xbmc.LOGDEBUG)


	def getParameters(self):
		args = [
			"--rtmp", '"%s"' % self.url,
			"--app", '"%s"' % self.app,
			#"--flashVer", '"WIN 10,3,183,7"',
			"--flashVer", '"WIN 11,0,1,152"',
			"--swfVfy", '"%s"' % self.swfPlayer,
			#"--pageUrl xxxxxx",
			"--conn", "Z:",
			"--playpath", '"%s"' % self.playPath,
			"-o", '"%s"' % self.savePath
			]

		command = ' '.join(args)

		log("command: " + command, xbmc.LOGDEBUG)
		return command

	def getPlayUrl(self):

		playURL = "%s?ovpfv=1.1&%s playpath=%s swfurl=%s swfvfy=true" % (self.url,self.auth,self.playPath,self.swfPlayer)

		log("playURL: " + playURL, xbmc.LOGDEBUG)
		return playURL

	

#TODO Add more comprehensive debug logging to this class (EpisodeList)
#TODO There is much reliance on member variables. Probably many cases 
#     where member variables are redundant or can be replaced by local vars passed
#     as parameters or returned from methods. Clean up.

#==================================================================================
# EpisodeList
#
# This class exists to provide two methods that have very similar functionality
# but with a minimum of code duplication
#
# Those methods are
# 1) Parse a web page that lists episodes of a show and create an XBMC list item
#    for each episode
#
# 2) Parse the SAME web page to find a particular episode  
#==================================================================================

class EpisodeList:

	def __init__(self):
		self.assetId 		= ''

	def getAssetId(self):
		return self.assetId


	def getHTML(self):
		return self.html


	def initialise(self, showId, showTitle):
		method = "EpisodeList.initialise"
		log ("initialise showId: %s, showTitle: %s " % ( showId, showTitle ), xbmc.LOGDEBUG)
		self.html = geturllib.GetURL( "http://www.channel4.com/programmes/" + showId + "/4od", 20000 ) # ~6 hrs

		if self.html == '':
			error = ErrorHandler('EpisodeList.initialise', 'Error getting episode list web page', 'See previous error')
			return error

		self.swfPlayer = GetSwfPlayer( self.html )

		(self.genre, error) = findString(method, '<meta name="primaryBrandCategory" content="(.*?)"/>', self.html)
		if error is not None:
			# Can't determine genre
			error.process(__language__(30710), "", xbmc.LOGWARNING)
			self.genre = ''

		(ol, error) = findString(method, '<ol class="all-series">(.*?)</div>', self.html)
		if error is not None:
			return error						

		self.listItemsHtml = re.findall( '<li(.*?[^p])>', ol, re.DOTALL | re.IGNORECASE )
		self.showId = showId
		self.showTitle = showTitle

		return None

	def getEpisodeDetails(self, htmlListItem):
		
		dataKeyValues = re.findall('data-([a-zA-Z\-]*?)="(.*?)"', htmlListItem, re.DOTALL | re.IGNORECASE )
		assetId		= ''
		url		= ''
		image		= ''
		premieredDate	= ''
		progTitle	= ''
		epTitle		= ''
		description	= ''
		epNum		= ''
		seriesNum	= ''


		for dataKeyValue in dataKeyValues:
			if ( dataKeyValue[0].lower() == 'episode-number' ):
				try: 
					epNum 	= int(dataKeyValue[1])
				except:
					pass
				continue

			if ( dataKeyValue[0].lower() == 'assetid' ):
				assetId		= dataKeyValue[1]
				continue 
			if ( dataKeyValue[0].lower() == 'episodeurl' ):
				url		= dataKeyValue[1]
				continue
			if ( dataKeyValue[0].lower() == 'image-url'):
				image		= dataKeyValue[1]
				continue
			if ( dataKeyValue[0].lower()  == 'txdate'):
				dateParts = dataKeyValue[1].split()
				if len(dateParts) == 3:
					if len(dateParts[0]) == 1:
						dateParts[0] = '0' + dateParts[0]

					dateParts[1] = (dateParts[1])[0:3]

					premieredDate = "%s %s %s" % (dateParts[0], dateParts[1], dateParts[2])
				else:
					premieredDate = dataKeyValue[1]

				continue

			if ( dataKeyValue[0].lower()  == 'episodetitle' ):
				progTitle	= dataKeyValue[1]
				continue
			if ( dataKeyValue[0].lower()  == 'episodeinfo' ):
				epTitle		= dataKeyValue[1]
				continue
			if ( dataKeyValue[0].lower()  == 'episodesynopsis' ):
				description	= dataKeyValue[1]
				continue
			if ( dataKeyValue[0].lower() == 'series-number' ):
				try: 
					seriesNum = int(dataKeyValue[1])
				except:
					pass
				continue


		if assetId <> '':
			log ('Episode details: ' + str((assetId,epNum,url,image,premieredDate,progTitle,epTitle,description,seriesNum)), xbmc.LOGDEBUG)
			self.assetId 		= assetId
			self.epNum 		= epNum
			self.url 		= url
			self.image 		= image
			self.premieredDate 	= premieredDate
			self.progTitle 		= progTitle
			self.epTitle 		= epTitle
			self.description	= description
			self.seriesNum		= seriesNum


	def refineEpisodeDetails(self):
		if ( self.seriesNum <> "" and self.epNum <> "" ):
			self.filename = self.showId + ".s%0.2ie%0.2i" % (self.seriesNum, self.epNum)
		elif len(self.premieredDate) > 0:
			self.filename = self.showId + "." + self.premieredDate.replace( ' ', '.' )
		else:
			self.filename = self.showId + "." + self.assetId

		self.progTitle = self.progTitle.strip()
		self.progTitle = self.progTitle.replace( '&amp;', '&' )
		self.epTitle = self.epTitle.strip()
		self.showTitle = remove_extra_spaces(remove_square_brackets(self.showTitle))
		if ( self.progTitle == self.showTitle and self.epTitle <> "" ):
			self.label = self.epTitle
		else:
			self.label = self.progTitle

		if self.label == '':
			self.label = self.showTitle

		if len(self.premieredDate) > 0 and self.premieredDate not in self.label:
				self.label = self.label + '  [' + self.premieredDate + ']'

		self.description = remove_extra_spaces(remove_html_tags(self.description))
		self.description = self.description.replace( '&amp;', '&' )
		self.description = self.description.replace( '&pound;', '£' )
		self.description = self.description.replace( '&quot;', "'" )

		if (self.image == ""):
			(self.thumbnail, error) = findString('EpisodeList.refineEpisodeDetails', '<meta property="og:image" content="(.*?)"', self.html)
			if error is not None:
				# Error getting image
				error.process(__language__(30715), "", xbmc.LOGWARNING)
				self.thumbnail = ''

		else:
			self.thumbnail = "http://www.channel4.com" + self.image


	def createNewListItem(self):
		newListItem = xbmcgui.ListItem( self.label )
		newListItem.setThumbnailImage(self.thumbnail)

		infoLabels = {'Title': self.label, 'Plot': self.description, 'PlotOutline': self.description, 'Genre': self.genre, 'premiered': self.premieredDate}

		if self.epNum <> '':
			infoLabels['Episode'] = self.epNum
 
		newListItem.setInfo('video', infoLabels)

		return newListItem


	#==============================================================================
	# createListItems
	#
	# Create an XBMC list item for each episode
	#==============================================================================
	def createListItems(self):
		
	        listItems = []
	        epsDict = dict()

	        for listItemHtml in self.listItemsHtml:
	                self.getEpisodeDetails(listItemHtml)

	                if (self.assetId == ''):
        	                continue;

    		        if ( self.assetId in epsDict ):
				continue

        	        epsDict[self.assetId] = 1

			self.refineEpisodeDetails()
                
	                newListItem = self.createNewListItem( )
	                url = __BaseURL__ + '?ep=' + mycgi.URLEscape(self.assetId) + "&show=" + mycgi.URLEscape(self.showId) + "&title=" + mycgi.URLEscape(self.label) + "&fn=" + mycgi.URLEscape(self.filename) + "&swfPlayer=" + mycgi.URLEscape(self.swfPlayer)

	                listItems.append( (url,newListItem,False) )


		return listItems


	#==============================================================================
	# createListItems
	#
	# Create a single XBMC list item for one particular episode
	#==============================================================================
	def createNowPlayingListItem(self, matchingAssetId):
		
	        for listItemHtml in self.listItemsHtml:
	                self.getEpisodeDetails(listItemHtml)

	                if (self.assetId <> matchingAssetId):
        	                continue;

			self.label = ''
			self.thumbnail = ''
			self.refineEpisodeDetails()

			newListItem = self.createNewListItem()
			return newListItem



#==============================================================================
# ShowCategories
#
# List the programme categories, retaining the 4oD order
#==============================================================================

def ShowCategories():
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/4od", 200000 ) # ~2 days

	if html == '':
		error = ErrorHandler('ShowCategories', 'Error getting category web page', 'See previous error')
		# 'Cannot show categories','Error getting category web page'
		error.process(__language__(30765), __language__(30770), xbmc.LOGERROR)
		return error

	html = re.findall( '<ol class="display-cats">(.*?)</div>', html, re.DOTALL | re.IGNORECASE )[0]
	categories = re.findall( '<a href="/programmes/tags/(.*?)/4od">(.*?)</a>', html, re.DOTALL | re.IGNORECASE )
	
	listItems = []
	# Start with a Search entry	'Search'
	newListItem = xbmcgui.ListItem( __language__(30500) )
	url = __BaseURL__ + '?search=1'
	listItems.append( (url,newListItem,True) )
	for categoryInfo in categories:
		label = remove_extra_spaces(remove_html_tags(categoryInfo[1]))
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
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/%s/4od%s" % (category, order), 40000 ) # ~12 hrs

	if html == '':
		error = ErrorHandler('AddExtraLinks', 'Error getting programme list web page', 'See previous error')
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
			thumbnail = remove_leading_slash(thumbnail)

		thumbnailPath = GetThumbnailPath(thumbnail)
		newLabel = ' [' + extraInfo[1] + ' ' + remove_extra_spaces(remove_brackets(label))+ ']'
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
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/%s/4od%s/brand-list/page-%s" % (category, order, page), 40000 ) # ~12 hrs

	if html == '':
		error = ErrorHandler('AddPageToListItems', 'Error getting programme list web page', 'See previous error')
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

	(nextUrl, error) = findString('AddPageToListItems', '<ol class="promo-container" data-nexturl="(.*?)"', html)
	if error is not None:
		# 'Error finding next page', 'Cannot determine if this is the last page or not'
		error.process(__language__(30720), __language__(30725), '', xbmc.LOGERROR)
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


def GetSwfPlayer( html ):
	log ("html size:" + str(len(html)), xbmc.LOGDEBUG)

	error = None

	(swfRoot, error) = findString('GetSwfPlayer', 'var swfRoot = \'(.*?)\'', html)
	if error is None:

		(fourodPlayerFile, error) = findString('GetSwfPlayer', 'var fourodPlayerFile = \'(.*?)\'', html)
		if error is None:

			#TODO Find out how to get the "asset/flash/swf/" part dynamically
			swfPlayer = "http://www.channel4.com" + swfRoot + "asset/flash/swf/" + fourodPlayerFile

			try:
				# Resolve redirect, if any
				req = urllib2.Request(swfPlayer)
				res = urllib2.urlopen(req)
				swfPlayer = res.geturl()
			except Exception, e:
				# Exception resolving swfPlayer URL
				error = ErrorHandler('GetSwfPlayer', __language__(30730), str(e))

	if error is not None:
		swfPlayer = __SwfPlayerDefault__
		# Unable to determine swfPlayer URL. Using default: 
		error.process(__language__(30520), __SwfPlayerDefault__, xbmc.LOGWARNING)
	
	return swfPlayer


#==============================================================================

def ShowEpisodes( showId, showTitle ):
	episodeList = EpisodeList()

	error = episodeList.initialise(showId, showTitle)
	if error is not None:
		# "Error parsing html", "Cannot list episodes."
		error.process(__language__(30735), __language__(30740), xbmc.LOGERROR)
		return

	listItems = episodeList.createListItems()

	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='episodes')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )

#==============================================================================

def SetSubtitles(episodeId, filename = None):
	subtitle = geturllib.GetURL( "http://ais.channel4.com/subtitles/%s" % episodeId, 0 )
	
	log('Subtitle code: ' + str(geturllib.GetLastCode()), xbmc.LOGDEBUG )
	log('Subtitle filename: ' + str(filename), xbmc.LOGDEBUG)
	log('Subtitle file length: ' + str(len(subtitle)), xbmc.LOGDEBUG)
	log('geturllib.GetLastCode(): ' + str(geturllib.GetLastCode()), xbmc.LOGDEBUG)

	if (geturllib.GetLastCode() == 404 or len(subtitle) == 0):
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
		return
		
	# Ensure default download folder is defined
	downloadFolder = __addon__.getSetting('download_folder')
	if downloadFolder is '':
		d = xbmcgui.Dialog()
		# Download Error - You have not set the default download folder.\n Please update the addon settings and try again.','','')
		d.ok(__language__(30560),__language__(30580),'','')
		__addon__.openSettings(sys.argv[ 0 ])
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

def Play(rtmp, showId, episodeId, title):
	log ('Play showId: ' + showId)
	log ('Play episodeId: ' + episodeId)
	log ('Play titleId: ' + title)

	playURL = rtmp.getPlayUrl()		
	
	episodeList = EpisodeList()
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
	player = xbmc.Player(xbmc.PLAYER_CORE_AUTO)
	player.play(play)

	subtitles = __addon__.getSetting( 'subtitles' )

	if (subtitles == 'true'):
		subtitleFile = SetSubtitles(episodeId)
		xbmc.Player().setSubtitles(subtitleFile)

#==============================================================================

def Download(rtmp, defaultFilename):
	(rtmpdumpPath, downloadFolder, filename) = GetDownloadSettings(defaultFilename)
	
	savePath = os.path.join( downloadFolder, filename )

	rtmp.setDownloadDetails(rtmpdumpPath, savePath)

	parameters = rtmp.getParameters()

	from subprocess import Popen, PIPE, STDOUT
		
	# Starting download
	log ("Starting download: " + rtmpdumpPath + " " + str(parameters))
	xbmc.executebuiltin('XBMC.Notification(4oD %s, %s)' % ( __language__(30610), filename))

	subtitles = __addon__.getSetting( 'subtitles' )

	if (subtitles == 'true'):
		log ("Getting subtitles")
		# '.flv' or other 3 character extension
		SetSubtitles(episodeId, savePath[0:-4] + '.smi')

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
	(token, error) = findString('GetAuthentication', '<token>(.*?)</token>', uriData)
	if error is not None:
		return error
		
	(cdn, error) = findString('GetAuthentication', '<cdn>(.*?)</cdn>', uriData)
	if error is not None:
		return error
		
	decodedToken = fourOD_token_decoder.Decode4odToken(token)

	if ( cdn ==  "ll" ):
		(e, error) = findString('GetAuthentication', '<e>(.*?)</e>', uriData)
		if error is not None:
			return error
	
		ip = re.search( '<ip>(.*?)</ip>', uriData, re.DOTALL | re.IGNORECASE )
		if (ip):
			auth = "e=%s&ip=%s&h=%s" % (e,ip.group(1),decodedToken)
		else:
			auth = "e=%s&h=%s" % (e,decodedToken)
	else:
		(fingerprint, error) = findString('GetAuthentication', '<fingerprint>(.*?)</fingerprint>', uriData)
		if error is not None:
			return error
	
		(slist, error) = findString('GetAuthentication', '<slist>(.*?)</slist>', uriData)
		if error is not None:
			return error
	
		auth = "auth=%s&aifp=%s&slist=%s" % (decodedToken,fingerprint,slist)

	return auth
	

#==============================================================================

def GetStreamInfo(episodeId):
	xml = geturllib.GetURL( "http://ais.channel4.com/asset/%s" % episodeId, 0 )
	if xml == '':
		error = ErrorHandler('GetStreamInfo', 'Error getting stream info xml', 'See previous error')
		return error

	(uriData, error) = findString('GetStreamInfo', '<uriData>(.*?)</uriData>', xml)
	if error is not None:
		return error
		
	(streamURI, error) = findString('GetStreamInfo', '<streamUri>(.*?)</streamUri>', uriData)
	if error is not None:
		return error
		

	# If HTTP Dynamic Streaming is used for this show then there will be no mp4 file,
	# and decoding the token will fail, therefore we abort before
	# parsing authentication info if there is no mp4 file.
	if 'mp4:' not in streamURI.lower():
		error = ErrorHandler('GetStreamInfo', __language__(30550), 'No MP4 found, probably HTTP Dynamic Streaming. Stream URI -\n' + streamURI + '\n')
		return error

	auth =  GetAuthentication(uriData)
	
	if isinstance(auth, ErrorHandler):
		return auth

	return (streamURI, auth)

#==============================================================================

def GetAction():
	actionSetting = __addon__.getSetting( 'select_action' )
	log ("action: " + actionSetting, xbmc.LOGDEBUG)

	# Ask
	if ( actionSetting == __language__(30120) ):
		dialog = xbmcgui.Dialog()
		# Do you want to play or download?	
		action = dialog.yesno(title, __language__(30530), '', '', __language__(30140),  __language__(30130)) # 1=Play; 0=Download
	# Download
	elif ( actionSetting == __language__(30140) ):
		action = 0
	else:
		action = 1

	return action

#==============================================================================

def InitialiseRTMP(episodeId, swfPlayer):
	# Get the stream info
	details = GetStreamInfo(episodeId)

	if isinstance(details, ErrorHandler):
		return details
		
	(streamUri, auth) = details

	rtmp = RTMP()
	error = rtmp.setDetailsFromURI(streamUri, auth, swfPlayer)

	if error is not None:
		return error

	return rtmp

#==============================================================================

def PlayOrDownloadEpisode( showId, episodeId, title, defaultFilename, swfPlayer ):
	log ('PlayOrDownloadEpisode showId: ' + showId, xbmc.LOGDEBUG)
	log ('PlayOrDownloadEpisode episodeId: ' + episodeId, xbmc.LOGDEBUG)
	log ('PlayOrDownloadEpisode title: ' + title, xbmc.LOGDEBUG)

	
	rtmp = InitialiseRTMP(episodeId, swfPlayer)
	if isinstance(rtmp, ErrorHandler):
		error = rtmp
		# 'Error parsing stream info', 'Cannot proceed'
		error.process(__language__(30750), __language__(30755), xbmc.LOGERROR)
		return

	action = GetAction()	

	if ( action == 1 ):
		# Play
		Play(rtmp, showId, episodeId, title)
		
	else:
		# Download
		Download(rtmp, defaultFilename)

	return

#==============================================================================

def DoSearch():
	# Search
	kb = xbmc.Keyboard( "", __language__(30500) )
	kb.doModal()
	if ( kb.isConfirmed() == False ): return
	query = kb.getText()
	DoSearchQuery( query )

#==============================================================================

def DoSearchQuery( query ):
	data = geturllib.GetURL( "http://www.channel4.com/search/predictive/?q=%s" % mycgi.URLEscape(query), 10000 )
	if data == '':
		error = ErrorHandler('DoSearchQuery', 'Error getting search web page', 'See previous error')
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

		(showId, error) = findString('DoSearchQuery', 'programmes/(.*?)/4od', progUrl)
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

def remove_leading_slash(data):
    p = re.compile(r'/')
    return p.sub('', data)

def remove_square_brackets(data):
    p = re.compile(r' \[.*?\]')
    return p.sub('', data)

def remove_brackets(data):
    p = re.compile(r' \(.*?\)')
    return p.sub('', data)

def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def remove_extra_spaces(data):
    p = re.compile(r'\s+')
    return p.sub(' ', data)



#==============================================================================

#def InitTimeout():
#	log("getdefaulttimeout(): " + str(getdefaulttimeout()), xbmc.LOGDEBUG)
#	environment = os.environ.get( "OS", "xbox" )
#	if environment in ['Linux', 'xbox']:
#		try:
#			timeout = int(__addon__.getSetting('socket_timeout'))
#			if (timeout > 0):
#				setdefaulttimeout(timeout)
#		except:
#			setdefaulttimeout(None)
#			pass




#==============================================================================

if __name__ == "__main__":

	try:
        	if __addon__.getSetting('http_cache_disable') == 'false':
			geturllib.SetCacheDir( CACHE_FOLDER )

#		InitTimeout()
    
		if ( mycgi.EmptyQS() ):
			ShowCategories()
		else:
			(category, showId, episodeId, title, search, swfPlayer, order, page) = mycgi.Params( 'category', 'show', 'ep', 'title', 'search', 'swfPlayer', 'order', 'page' )

			if ( search <> '' ):
				DoSearch()
			elif ( showId <> '' and episodeId == ''):
				ShowEpisodes( showId, title )
			elif ( category <> '' ):
				ShowCategory( category, title, order, page )
			elif ( episodeId <> '' ):
				PlayOrDownloadEpisode( showId, episodeId, title, mycgi.Param('fn'), swfPlayer )
	except:
		# Make sure the text from any script errors are logged
		import traceback
		traceback.print_exc(file=sys.stdout)
		raise

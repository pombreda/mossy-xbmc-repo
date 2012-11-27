# -*- coding: utf-8 -*-
import re
from time import mktime,strptime
from datetime import timedelta
from datetime import date
import sys

import xbmcplugin
import xbmcgui
import xbmc
from xbmc import log

import mycgi
import utils
from loggingexception import LoggingException
import rtmp

from provider import Provider
from BeautifulSoup import BeautifulSoup          # For processing HTML
from BeautifulSoup import BeautifulStoneSoup

__urlRoot__ = "http://www.rte.ie"
__rootMenuUrl__ = "http://www.rte.ie/player/ie/"
__searchUrl__ = "http://www.rte.ie/player/ie/search/?q="
__swfDefault__ = "http://www.rte.ie/static/player/swf/osmf2_2012_10_19.swf"
__flashJS__ = "http://static.rasset.ie/static/player/js/flash-player.js"
__feedUrlRoot__ = "http://feeds.rasset.ie/rteavgen/player/playlist/?type=iptv&format=json&showId="
__showUrl__ = "http://www.rte.ie/player/ie/show/%s/"

class RTEProvider(Provider):

#	def __init__(self):
#		self.cache = cache

	def GetProviderId(self):
		return "RTE"

	def ExecuteCommand(self, mycgi):
		return super(RTEProvider, self).ExecuteCommand(mycgi)

	def ShowRootMenu(self):
		log("RTEProvider::ShowRootMenu", xbmc.LOGDEBUG)
		(html, logLevel) = self.cache.GetURLFromCache(__rootMenuUrl__, 20000)

		if html is None or html == '':
			# Error getting RTE Player "Home" page
			logException = LoggingException("RTEProvider::ShowRootMenu", self.language(20000))
			# 'Cannot show RTE root menu', Error getting RTE Player "Home" page
			logException.process(self.language(20010), self.language(20000), logLevel)
			#raise logException
			return False

		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		categories = soup.find('div', "dropdown-programmes")

		if categories == None:
			# "Can't find dropdown-programmes"
			logException = LoggingException("RTEProvider::ShowRootMenu", self.language(20020))
			# 'Cannot show RTE root menu', Error parsing web page
			logException.process(self.language(20010), self.language(30780), logLevel)
			#raise logException
			return False
		
		listItems = []

		newLabel = "Search"
		thumbnailPath = utils.GetThumbnailPath(newLabel)
		newListItem = xbmcgui.ListItem( label=newLabel.replace('&#39;', "'" ) )
		newListItem.setThumbnailImage(thumbnailPath)
		url = self.GetURLStart() + '&search=1'
		listItems.append( (url, newListItem, True) )

		self.AddAllLinks(listItems, categories)		

		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
		
		return True

	# listshows: If '1' list the shows on the main page, otherwise process the sidebar. The main page links to programmes or specific episodes, the sidebar links to categories or sub-categories
	# episodeId: id of the show to be played, or the id of a show where more than one episode is available
	# listavailable: If '1' process the specified episode as one of at least one episodes availabe, i.e. list all episodes available
	# search: If '1' perform a search
	# page: url, relative to www.rte.ie, to be processed. Not passed when an episodeId is given.

	def ParseCommand(self, mycgi):
		(listshows, episodeId, listAvailable, search, page) = mycgi.Params( 'listshows', 'episodeId', 'listavailable', 'search', 'page' )
		log("RTEProvider::ParseCommand", xbmc.LOGDEBUG)
		log("listshows: %s, episodeId %s, listAvailable %s, search %s, page %s" % (str(listshows), episodeId, str(listAvailable), str(search), page), xbmc.LOGDEBUG)

		if search <> '':
			return self.DoSearch()
		
		if episodeId <> '':
			return self.PlayEpisode(episodeId)

		if page == '':
			# "Can't find 'page' parameter "
			logException = LoggingException("RTEProvider::ParseCommand", self.language(30030))
			# 'Cannot proceed', Error processing command
			logException.process(self.language(30010), self.language(30780), logLevel)
			return False

		# TODO Test this
		log("page = %s" % page, xbmc.LOGDEBUG)
		page = mycgi.URLUnescape(page)
		log("mycgi.URLUnescape(page) = %s" % page, xbmc.LOGDEBUG)

		if ' ' in page:
			page = page.replace(' ', '%20')

		(html, logLevel) = self.cache.GetURLFromCache( __urlRoot__ + page, 1800 )
		if html is None or html == '':
			# Data returned from web page: %s, is: '%s'
			logException = LoggingException("RTEProvider::ParseCommand", self.language(30060) % ( __urlRoot__ + page, str(html)))

			# Error getting web page
			logException.process(self.language(30050), '', logLevel)
			return False
		
		if listshows <> '':
			return self.ListShows(html)
		
		if listAvailable <> '':
			return self.ListAvailable(html)

		return self.ListSubMenu(html)

#==============================================================================

	def AddAllLinks(self, listItems, html, listshows = False):
		for link in html.findAll('a'):
			page = link['href']
			newLabel = link.contents[0]
			thumbnailPath = utils.GetThumbnailPath(newLabel.replace(' ', ''))
			newListItem = xbmcgui.ListItem( label=newLabel.replace('&#39;', "'" ))
			newListItem.setThumbnailImage(thumbnailPath)

			url = self.GetURLStart() + '&page=' + mycgi.URLEscape(page)

			# "Most Popular" does not need a submenu, go straight to episode listing
			if listshows or "Popular" in newLabel:
				url = url + '&listshows=1'

			log("RTEProvider::AddAllLinks url: %s" % url, xbmc.LOGDEBUG)
			listItems.append( (url,newListItem,True) )
			

#==============================================================================

	def ListAToZ(self, atozTable):
		log("RTEProvider::ListAToZ", xbmc.LOGDEBUG)
		listItems = []

		self.AddAllLinks(listItems, atozTable, True)		

		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
		

		return True
		

#==============================================================================

	def ListSubMenu(self, html):
		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		aside = soup.find('aside')

		if aside is None:
			return self.ListLatest(soup)

		atozTable = soup.find('table', 'a-to-z')
		
		if atozTable is not None:
			return self.ListAToZ(atozTable)

		listItems = []

		categories = aside.findAll('a')
		for category in categories:
			href = category['href']
			
			title = category.contents[0]

			newListItem = xbmcgui.ListItem( label=title.replace('&#39;', "'" ) )
			newListItem.setThumbnailImage(title.replace(' ', ''))
			url = self.GetURLStart() + '&page=' + mycgi.URLEscape(href) + '&listshows=1'
			listItems.append( (url, newListItem, True) )
			log("RTEProvider::ListSubMenu url: %s" % url, xbmc.LOGDEBUG)
		
		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )

		return True

#==============================================================================

	def ListLatest(self, soup):
		log("RTEProvider::ListLatest", xbmc.LOGDEBUG)
		listItems = []

		calendar = soup.find('table', 'calendar')

		links = calendar.findAll('a')
		links.reverse()
		for link in links:
			page = link['href']

			match=re.search( "/([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])/", page)

			today = date.today()
			# TODO Handle Exceptions
			if match is None:
				continue;

			linkDate = date.fromtimestamp(mktime(strptime(match.group(1), "%Y-%m-%d")))
			
			daysAgo = today - linkDate
			if daysAgo == timedelta(0):
				newLabel = "Today"
			elif daysAgo == timedelta(1):
				newLabel = "Yesterday"
			elif daysAgo == timedelta(2) or daysAgo == timedelta(3):
				newLabel = linkDate.strftime("%A")
			else:
				newLabel = linkDate.strftime("%A, %d %B %Y")
				

			newListItem = xbmcgui.ListItem( label=newLabel.replace('&#39;', "'" ))

			url = self.GetURLStart() + '&page=' + mycgi.URLEscape(page) + '&listshows=1'
			listItems.append( (url,newListItem,True) )

		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
		
		return True


#==============================================================================

	def AddEpisodeToList(self, listItems, episode):
		href = episode['href']
		title = episode.find('span', "thumbnail-title").contents[0]
		date = episode.find('span', "thumbnail-date").contents[0]					

		newLabel = title + ", " + date
										
		newListItem = xbmcgui.ListItem( label=newLabel.replace('&#39;', "'" ) )
		newListItem.setThumbnailImage(episode.img['src'])
		infoLabels = self.GetEpisodeInfo(self.GetEpisodeIdFromURL(href))
		newListItem.setInfo('video', infoLabels)

		#log("RTEProvider::AddEpisodeToList label == " + newLabel, xbmc.LOGDEBUG)

		if "episodes available" in date:
			url = self.GetURLStart()  + '&listavailable=1' + '&page=' + mycgi.URLEscape(href)
		else:
			match = re.search( "/player/ie/show/([0-9]+)/", href )
			if match is None:
				pass
				# Exception
		
			episodeId = match.group(1)

			url = self.GetURLStart() + '&episodeId=' +  mycgi.URLEscape(episodeId)

		listItems.append( (url, newListItem, True) )
	

#==============================================================================

	def ListShows(self, html):
		log("RTEProvider::ListShows", xbmc.LOGDEBUG)
		listItems = []

		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		episodes = soup.findAll('a', "thumbnail-programme-link")

		for episode in episodes:
			self.AddEpisodeToList(listItems, episode)

		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
		

		return True

#==============================================================================

	def AddEpisodeToSearchList(self, listItems, article):
		episodeLink = article.find('a', "thumbnail-programme-link")
		href = episodeLink['href']

		titleTag = article.find('h3', "search-programme-title").a.contents

		#TODO Find a neater way of doing this
		if len(titleTag) == 2:
			title = ''

			if titleTag[0].__class__.__name__ == "Tag":
				title = titleTag[0].string
			else:
				title = titleTag[0]
		

			if titleTag[1].__class__.__name__ == "Tag":
				title = title + titleTag[1].string
			else:
				title = title + titleTag[1]

		else:
			title = "Unknown"

		#TODO Find out why Soup is choking on this:
#  <article class="search-result clearfix"><a
#        href="/player/ie/show/10090749/" class="thumbnail-programme-link"><span
#            class="sprite thumbnail-icon-play">Watch Now</span><img class="thumbnail" alt="Watch Now"
#            src="http://img.rasset.ie/0006b156-261.jpg"></a>
#    <h3 class="search-programme-title"><a href="/player/ie/show/10090749/"><span class="search-highlight">News</span> on Two and World Forecast</a></h3>
#    <p class="search-programme-episodes"><a href="/player/ie/show/10090749/">Mon 26 Nov 2012</a></p>
#    <!-- p class="search-programme-date">26/11/2012</p -->
#    <p class="search-programme-description">All the <span class="search-highlight">news</span> and sport from home and abroad.</p>
#     <span
#        class="sprite logo-rte-two search-channel-icon">RTÉ 2</span>
#  </article>

		# p class="search-programme-episodes"
		#date = article.find('p', "search-programme-episodes").a.contents
		date = '' # Temporary

		#newLabel = title + ", " + date
		newLabel = title
										
		newListItem = xbmcgui.ListItem( label=newLabel.replace('&#39;', "'" ) )
		#newListItem.setThumbnailImage(episode.img['src'])
		infoLabels = self.GetEpisodeInfo(self.GetEpisodeIdFromURL(href))
		newListItem.setInfo('video', infoLabels)

		#log("RTEProvider::AddEpisodeToList label == " + newLabel, xbmc.LOGDEBUG)

		if "episodes available" in date:
			url = self.GetURLStart()  + '&listavailable=1' + '&page=' + mycgi.URLEscape(href)
		else:
			match = re.search( "/player/ie/show/([0-9]+)/", href )
			if match is None:
				pass
				# Exception
		
			episodeId = match.group(1)

			url = self.GetURLStart() + '&episodeId=' +  mycgi.URLEscape(episodeId)

		listItems.append( (url, newListItem, True) )
	

#==============================================================================

	def ListSearchShows(self, html):
		log("RTEProvider::ListSearchShows", xbmc.LOGDEBUG)
		listItems = []

		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		articles = soup.findAll("article", "search-result clearfix")

		for article in articles:
			self.AddEpisodeToSearchList(listItems, article)

		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
		

		return True

#==============================================================================

	def ListAvailable(self, html):
		log("RTEProvider::ListAvailable", xbmc.LOGDEBUG)
		listItems = []
		
		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		# TODO Exception if not found
		count = int(soup.find('meta', { 'name' : "episodes_available"} )['content'])

		availableEpisodes = soup.findAll('a', "thumbnail-programme-link")
		
		for index in range ( 0, count ):
			self.AddEpisodeToList(listItems, availableEpisodes[index])
		
		xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
		xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )

		return True


#==============================================================================

	# Download the given url and return the first string that matches the pattern
	def GetStringFromURL(self, url, pattern, maxAge = 20000):
		log("RTEProvider::GetStringFromURL url '%s', pattern '%s'" % (url, pattern), xbmc.LOGDEBUG)

		(data, logLevel) = self.cache.GetURLFromCache(url, maxAge)

		if data is None or data == '':
			# Log error
			return None

		log("RTEProvider::GetStringFromURL len(data): " + str(len(data)), xbmc.LOGDEBUG)

		match = re.search(pattern, data)
		
		if match is None or match.groups() is None:
			# Log error
			# Can't find pattern in string
			messageLog = "\nPattern - \n%s\n\nString - \n%s\n\n" % (pattern, data[0:10000])
			log("RTEProvider::GetStringFromURL " + messageLog, xbmc.LOGERROR)
			return None

		return match.groups()
#		string = match.group(1)

#		if string is None or string == '':
#			# Log error
#			return None
		
#		log("RTEProvider::GetStringFromURL string '%s'" % string, xbmc.LOGDEBUG)

#==============================================================================

	# Download the given url and return the Match object containing the first set of data matching the pattern
	#def GetMatchFromURL(self, url, pattern, maxAge = 20000):
	#	log("RTEProvider::GetMatchFromURL url '%s', pattern '%s'" % (url, pattern), xbmc.LOGDEBUG)

#==============================================================================

	def GetSWFPlayer(self):
		log("RTEProvider::GetSWFPlayer", xbmc.LOGDEBUG)

		(javascript, logLevel) = self.cache.GetURLFromCache(__flashJS__, 50000)

		if javascript is None or javascript == '':
			# Log error
			return __swfDefault__

		match=re.search("\"(http://.+swf)", javascript)
		if match is None:
			# Log error
			return __swfDefault__

		swfPlayer = match.group(1)

		if swfPlayer is None or javascript == '':
			# Log error
			return __swfDefault__

		return swfPlayer


#==============================================================================

	def GetThumbnailFromEpisode(self, episodeId, soup = None):
		log("RTEProvider::GetThumbnailFromEpisode", xbmc.LOGDEBUG)
		if soup is None:
			(html, logLevel) = self.cache.GetURLFromCache(__showUrl__ % episodeId, 20000)

			# TODO Exception if not found
			soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])

		image = soup.find('meta', { 'property' : "og:image"} )['content']

		return image

#==============================================================================

	def GetEpisodeInfo(self, episodeId, soup = None):
		log("RTEProvider::GetEpisodeInfo", xbmc.LOGDEBUG)

		if soup is None:
			(html, logLevel) = self.cache.GetURLFromCache(__showUrl__ % episodeId, 20000)

			# TODO Exception if not found
			soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])

		title = soup.find('meta', { 'name' : "programme"} )['content']
		description = soup.find('meta', { 'name' : "description"} )['content']
		categories = soup.find('meta', { 'name' : "categories"} )['content']

		infoLabels = {'Title': title, 'Plot': description, 'PlotOutline': description, 'Genre': categories}

		log("RTEProvider::GetEpisodeInfo infoLabels: %s" % infoLabels, xbmc.LOGDEBUG)
		return infoLabels

#==============================================================================

	def PlayEpisode(self, episodeId):
		log("RTEProvider::PlayEpisode(%s)" % episodeId, xbmc.LOGDEBUG)
		
		swfPlayerGroup = self.GetStringFromURL(__flashJS__, "\"(http://.+swf)", 50000)
		if swfPlayerGroup is None:
			# Log error
			swfPlayer = __swfDefault__
		else:
			swfPlayer = swfPlayerGroup[0]

		(html, logLevel) = self.cache.GetURLFromCache(__showUrl__ % episodeId, 20000)

		soup = BeautifulSoup(''.join(html), selfClosingTags=['img'])
		# TODO Exception if not found
		feedsPrefix = soup.find('meta', { 'name' : "feeds-prefix"} )['content']

		infoLabels = self.GetEpisodeInfo(episodeId, soup)
		thumbnail = self.GetThumbnailFromEpisode(episodeId, soup)

		urlGroups = self.GetStringFromURL(feedsPrefix + episodeId, "\"url\": \"(/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/)([a-zA-Z0-9]+/)?(.+).f4m\"", 20000)
		if urlGroups is None:
			# Log error
			log("RTEProvider::PlayEpisode urlGroups is None", xbmc.LOGERROR)
			return False

		(urlDateSegment, extraSegment, urlSegment) = urlGroups

		rtmpStr = "rtmpe://fmsod.rte.ie:1935/rtevod"
		app = "rtevod"
		swfVfy = swfPlayer
		playPath = "mp4:%s%s/%s_512k.mp4" % (urlDateSegment, urlSegment, urlSegment)
		playURL = "%s app=%s playpath=%s swfurl=%s swfvfy=true" % (rtmp, app, playPath, swfVfy)


		rtmpvar = rtmp.RTMP(rtmp = rtmpStr, app = app, swfVfy = swfVfy, playPath = playPath)

		log("RTEProvider::PlayEpisode(%s) playUrl: %s" % (episodeId, playURL), xbmc.LOGDEBUG)
		
		return self.PlayOrDownloadEpisode(episodeId, infoLabels, thumbnail, rtmpvar)


	def GetEpisodeIdFromURL(self, url):
		segments = url.split("/")
		segments.reverse()

		for segment in segments:
			if segment <> '':
				return segment


	def Play(self, infoLabels, thumbnail, rtmpvar):
		log ('Play titleId: ' + infoLabels['Title'])

		listItem = xbmcgui.ListItem(infoLabels['Title'])
		listItem.setThumbnailImage(thumbnail)
		listItem.setInfo('video', infoLabels)

		play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
		play.clear()
		play.add(rtmpvar.getPlayUrl(), listItem)

		xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)


	def PlayOrDownloadEpisode(self, episodeId, infoLabels, thumbnail, rtmpvar):
		#log ('PlayOrDownloadEpisode showId: ' + showId, xbmc.LOGDEBUG)
		#log ('PlayOrDownloadEpisode episodeId: ' + episodeId, xbmc.LOGDEBUG)
		#log ('PlayOrDownloadEpisode title: ' + title, xbmc.LOGDEBUG)

		action = self.GetAction(infoLabels['Title'])

		if ( action == 1 ):
			# Play
			self.Play(infoLabels, thumbnail, rtmpvar)
	
		else:
			if ( action == 0 ):
				# Download
				defaultFilename = self.GetDefaultFilename(infoLabels['Title'], episodeId)
				self.Download(rtmpvar, episodeId, defaultFilename)

		return None

#==============================================================================

	def GetDefaultFilename(self, title, episodeId):
		if episodeId <> "":
			#E.g. NAME.s01e12
			return title + "_" + episodeId
	
		return title

#==============================================================================
#TODO Use shared Search memory
	def DoSearch(self):
		log("RTEProvider::DoSearch", xbmc.LOGDEBUG)
		# Search
		kb = xbmc.Keyboard( "", self.language(30500) )
		kb.doModal()
		if ( kb.isConfirmed() == False ): return
		query = kb.getText()

		return self.DoSearchQuery( query )

#==============================================================================

	def DoSearchQuery( self, query ):
		log("RTEProvider::DoSearchQuery(%s)" % query, xbmc.LOGDEBUG)
		(html, logLevel) = self.cache.GetURLFromCache( __searchUrl__ + mycgi.URLEscape(query), 1800 )
		if html is None or html == '':
			# Data returned from web page: %s, is: '%s'
			logException = LoggingException("RTEProvider::DoSearchQuery", self.language(30060) % ( __SEARCH__ + mycgi.URLEscape(query), html))

			# Error getting web page
			logException.process(self.language(30050), '', logLevel)
			return False

		self.ListSearchShows(html)

		return True



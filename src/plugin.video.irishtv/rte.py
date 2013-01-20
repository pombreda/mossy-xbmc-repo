# -*- coding: utf-8 -*-

import re
from time import mktime,strptime
from datetime import timedelta
from datetime import date
from datetime import datetime
import sys
from urlparse import urljoin

if hasattr(sys.modules["__main__"], "xbmc"):
    xbmc = sys.modules["__main__"].xbmc
else:
    import xbmc
    
if hasattr(sys.modules["__main__"], "xbmcgui"):
    xbmcgui = sys.modules["__main__"].xbmcgui
else:
    import xbmcgui

if hasattr(sys.modules["__main__"], "xbmcplugin"):
    xbmcplugin = sys.modules["__main__"].xbmcplugin
else:
    import xbmcplugin

import mycgi
import utils
from loggingexception import LoggingException
import rtmp

from provider import Provider
import HTMLParser

from BeautifulSoup import BeautifulSoup

urlRoot = u"http://www.rte.ie"
rootMenuUrl = u"http://www.rte.ie/player/ie/"
showUrl = u"http://www.rte.ie/player/ie/show/%s/"
feedUrl = u"http://feeds.rasset.ie/rteavgen/player/playlist/?type=iptv&format=json&showId="

flashJS = u"http://static.rasset.ie/static/player/js/flash-player.js"
configUrl = u"http://www.rte.ie/player/config/config.xml"

playerJSDefault = u"http://static.rasset.ie/static/player/js/player.js?v=5"
searchUrlDefault = u"http://www.rte.ie/player/ie/search/?q="
swfDefault = u"http://www.rte.ie/static/player/swf/osmf2_2012_10_19.swf"
swfLiveDefault = u"http://www.rte.ie/static/player/swf/osmf2_541_2012_11_14.swf"

class RTEProvider(Provider):

#    def __init__(self):
#        self.cache = cache

    def GetProviderId(self):
        return u"RTE"

    def ExecuteCommand(self, mycgi):
        return super(RTEProvider, self).ExecuteCommand(mycgi)

    def ShowRootMenu(self):
        self.log(u"", xbmc.LOGDEBUG)
        
        try:
            html = self.httpManager.GetWebPage(rootMenuUrl, 60).decode('utf8')
    
            if html is None or html == '':
                # Error getting %s Player "Home" page
                logException = LoggingException(self.language(20000) % self.GetProviderId())
                # 'Cannot show RTE root menu', Error getting RTE Player "Home" page
                logException.process(self.language(20010) % self.GetProviderId(), self.language(20000) % self.GetProviderId(), self.logLevel(xbmc.LOGERROR))
                return False
    
            soup = BeautifulSoup(html, selfClosingTags=['img'])
            categories = soup.find(u'div', u"dropdown-programmes")
    
            if categories == None:
                # "Can't find dropdown-programmes"
                logException = LoggingException(self.language(20020))
                # 'Cannot show RTE root menu', Error parsing web page
                logException.process(self.language(20010)  % self.GetProviderId(), self.language(30780), self.logLevel(xbmc.LOGERROR))
                #raise logException
                return False
            
            listItems = []
    
            try:
                listItems.append( self.CreateSearchItem() )
            except (Exception) as exception:
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)

                # Not fatal, just means that we don't have the search option
                exception.process(severity = xbmc.LOGWARNING)
    
            if False == self.AddAllLinks(listItems, categories, autoThumbnails = True):
                return False
            
            newLabel = u"Live"
            thumbnailPath = self.GetThumbnailPath(newLabel)
            newListItem = xbmcgui.ListItem( label=newLabel )
            newListItem.setThumbnailImage(thumbnailPath)
            url = self.GetURLStart() + u'&live=1'
            listItems.append( (url, newListItem, True) )
    
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
            
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error showing root menu
            exception.addLogMessage(self.language(40070))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    """
    listshows: If '1' list the shows on the main page, otherwise process the sidebar. The main page links to programmes or specific episodes, the sidebar links to categories or sub-categories
    episodeId: id of the show to be played, or the id of a show where more than one episode is available
    listavailable: If '1' process the specified episode as one of at least one episodes available, i.e. list all episodes available
    search: If '1' perform a search
    page: url, relative to www.rte.ie, to be processed. Not passed when an episodeId is given.
    live: If '1' show live menu
    """
    def ParseCommand(self, mycgi):
        (listshows, episodeId, listAvailable, search, page, live) = mycgi.Params( u'listshows', u'episodeId', u'listavailable', u'search', u'page', u'live' )
        self.log(u"", xbmc.LOGDEBUG)
        self.log(u"listshows: %s, episodeId %s, listAvailable %s, search %s, page %s" % (str(listshows), episodeId, str(listAvailable), str(search), page), xbmc.LOGDEBUG)

       
        if episodeId <> '':
            return self.PlayEpisode(episodeId.decode('utf8'))

        if search <> '':
            if page == '':
                return self.DoSearch()
            else:
                return self.DoSearchQuery( queryUrl = urlRoot + page)
                 
        if page == '':
            if live <> '':
                return self.ShowLiveMenu()
            
            # "Can't find 'page' parameter "
            logException = LoggingException(logMessage = self.language(30030))
            # 'Cannot proceed', Error processing command
            logException.process(self.language(30010), self.language(30780), self.logLevel(xbmcc.LOGERROR))
            return False

        page = page.decode('utf8')
        # TODO Test this
        self.log(u"page = %s" % page, xbmc.LOGDEBUG)
        page = mycgi.URLUnescape(page)
        self.log(u"mycgi.URLUnescape(page) = %s" % page, xbmc.LOGDEBUG)

        if u' ' in page:
            page = page.replace(u' ', u'%20')

        try:
            self.log(u"urlRoot: " + urlRoot + u", page: " + page )
            html = self.httpManager.GetWebPage( urlRoot + page, 1800 ).decode('utf8')
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error getting web page
            exception.addLogMessage(self.language(30050))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

        if live <> '':
            return self.PlayLiveTV(html)
            
        if listshows <> u'':
            return self.ListShows(html)
        
        if listAvailable <> u'':
            return self.ListAvailable(html)

        return self.ListSubMenu(html)


    def ShowLiveMenu(self):
        self.log(u"", xbmc.LOGDEBUG)

        defaultChannels = {u'RT\xc9 One' : u'/player/ie/live/8/', u'RT\xc9 News Now' : u'/player/ie/live/7/', u'RT\xc9 Two' : u'/player/ie/live/10/'}
        try:
            html = self.httpManager.GetWebPage(rootMenuUrl, 60).decode('utf8')
    
            soup = BeautifulSoup(html, selfClosingTags=['img'])
#            soup.find('aside', 'sidebar-content-box.clearfix').find('ul', 'sidebar-live-list')
            links = soup.find('ul', 'sidebar-live-list').findAll('a')
            
            listItems = []
            for link in links:
                channel = link.span.string
                programme = link.span.nextSibling.strip()
                page = link['href']
            
                if channel in defaultChannels:
                    del defaultChannels[channel]
                
                thumbnailPath = self.GetThumbnailPath((channel.replace(u'RT\xc9 ', '')).replace(' ', ''))
                newListItem = xbmcgui.ListItem( label=programme )
                newListItem.setThumbnailImage(thumbnailPath)
                url = self.GetURLStart() + u'&live=1' + u'&page=' + mycgi.URLEscape(page)
                listItems.append( (url, newListItem, True) )

            # Use default values for channel not found
            for channel in defaultChannels:
                thumbnailPath = self.GetThumbnailPath((channel.replace(u'RT\xc9 ', '')).replace(' ', ''))
                newListItem = xbmcgui.ListItem( label="Unknown" )
                newListItem.setThumbnailImage(thumbnailPath)
                url = self.GetURLStart() + u'&live=1' + u'&page=' + mycgi.URLEscape(defaultChannels[channel])
                listItems.append( (url, newListItem, True) )

            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
            
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error getting Live TV information
            exception.addLogMessage(self.language(40080))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    def CreateSearchItem(self, pageUrl = None):
        try:
            if pageUrl is None or len(pageUrl) == 0:
                newLabel = u"Search"
                url = self.GetURLStart() + u'&search=1'
            else:
                newLabel = u"More..."
                url = self.GetURLStart() + u'&search=1' + u'&page=' + mycgi.URLEscape(pageUrl)
  
            thumbnailPath = self.GetThumbnailPath("Search")
            newListItem = xbmcgui.ListItem( label=newLabel )
            newListItem.setThumbnailImage(thumbnailPath)
            
            return (url, newListItem, True)
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error creating Search item
            exception.addLogMessage(self.language(40220))
            raise exception

    #==============================================================================

    def AddAllLinks(self, listItems, html, listshows = False, autoThumbnails = False):
        htmlparser = HTMLParser.HTMLParser()
        
        try:
            for link in html.findAll(u'a'):
                page = link[u'href']
                newLabel = htmlparser.unescape(link.contents[0])
                thumbnailPath = self.GetThumbnailPath(newLabel.replace(u' ', u''))
                newListItem = xbmcgui.ListItem( label=newLabel)
                newListItem.setThumbnailImage(thumbnailPath)
    
                url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page)
    
                # "Most Popular" does not need a submenu, go straight to episode listing
                if listshows or u"Popular" in newLabel:
                    url = url + u'&listshows=1'
    
                self.log(u"url: %s" % url, xbmc.LOGDEBUG)
                listItems.append( (url,newListItem,True) )

            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error adding links
            exception.addLogMessage(self.language(40080))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    #==============================================================================

    def ListAToZ(self, atozTable):
        self.log(u"", xbmc.LOGDEBUG)
        listItems = []

        if False == self.AddAllLinks(listItems, atozTable, listshows = True):
            return False        

        xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
        xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )

        return True
        
    #==============================================================================

    def ListSubMenu(self, html):
        htmlparser = HTMLParser.HTMLParser()
        try:
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            aside = soup.find(u'aside')
    
            if aside is None:
                return self.ListLatest(soup)
    
            atozTable = soup.find(u'table', u'a-to-z')
            
            if atozTable is not None:
                return self.ListAToZ(atozTable)
    
            listItems = []
    
            categories = aside.findAll(u'a')
            for category in categories:
                href = category[u'href']
                
                title = htmlparser.unescape(category.contents[0])
    
                newListItem = xbmcgui.ListItem( label=title )
                newListItem.setThumbnailImage(title.replace(u' ', u''))
                url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(href) + u'&listshows=1'
                listItems.append( (url, newListItem, True) )
                self.log(u"url: %s" % url, xbmc.LOGDEBUG)
            
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
    
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error listing submenu
            exception.addLogMessage(self.language(40090))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    #==============================================================================
    
    def ListLatest(self, soup):
        self.log(u"", xbmc.LOGDEBUG)
        listItems = []
    
        calendar = soup.find(u'table', u'calendar')
    
        links = calendar.findAll(u'a')
        links.reverse()

        # Today
        page = links[0][u'href']
        newLabel = u"Today"
        newListItem = xbmcgui.ListItem( label=newLabel )
        match=re.search( u"/([0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?)/", page)
        if match is None:
            self.log(u"No date match for page href: '%s'" % page, xbmc.LOGWARNING)
        else:
            url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page) + u'&listshows=1'
            listItems.append( (url,newListItem,True) )
            
        # Yesterday
        page = links[1][u'href']
        newLabel = u"Yesterday"
        newListItem = xbmcgui.ListItem( label=newLabel )
        match=re.search( u"/([0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?)/", page)
        if match is None:
            self.log(u"No date match for page href: '%s'" % page, xbmc.LOGWARNING)
        else:
            url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page) + u'&listshows=1'
            listItems.append( (url,newListItem,True) )
        
        # Weekday
        page = links[2][u'href']
        match=re.search( u"/([0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?)/", page)
        if match is None:
            self.log(u"No date match for page href: '%s'" % page, xbmc.LOGWARNING)
        else:
            linkDate = date.fromtimestamp(mktime(strptime(match.group(1), u"%Y-%m-%d")))
                
            newLabel = linkDate.strftime(u"%A")
            newListItem = xbmcgui.ListItem( label=newLabel )

            url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page) + u'&listshows=1'
            listItems.append( (url,newListItem,True) )
        
        # Weekday
        page = links[3][u'href']
        match=re.search( u"/([0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?)/", page)
        if match is None:
            self.log(u"No date match for page href: '%s'" % page, xbmc.LOGWARNING)
        else:
            linkDate = date.fromtimestamp(mktime(strptime(match.group(1), u"%Y-%m-%d")))
                
            newLabel = linkDate.strftime(u"%A")
            newListItem = xbmcgui.ListItem( label=newLabel )

            url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page) + u'&listshows=1'
            listItems.append( (url,newListItem,True) )
        
        for link in links[4:]:
            page = link[u'href']
    
            match=re.search( u"/([0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?)/", page)
            if match is None:
                self.log(u"No date match for page href: '%s'" % page, xbmc.LOGWARNING)
                continue;
    
            linkDate = date.fromtimestamp(mktime(strptime(match.group(1), u"%Y-%m-%d")))
            
            newLabel = linkDate.strftime(u"%A, %d %B %Y")
            newListItem = xbmcgui.ListItem( label=newLabel)
    
            url = self.GetURLStart() + u'&page=' + mycgi.URLEscape(page) + u'&listshows=1'
            listItems.append( (url,newListItem,True) )
    
        xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
        xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
        
        return True
    
    
    #==============================================================================
    
    def AddEpisodeToList(self, listItems, episode):
        self.log(u"", xbmc.LOGDEBUG)
        htmlparser = HTMLParser.HTMLParser()

        href = episode[u'href']
        title = htmlparser.unescape( episode.find(u'span', u"thumbnail-title").contents[0] )
        date = episode.find(u'span', u"thumbnail-date").contents[0]                    
        #description = ...
        thumbnail = episode.find('img', 'thumbnail')['src']
    
        newLabel = title + u", " + date
                                        
        newListItem = xbmcgui.ListItem( label=newLabel )
        newListItem.setThumbnailImage(thumbnail)
        
        if self.addon.getSetting( u'RTE_descriptions' ) == 'true':
            infoLabels = self.GetEpisodeInfo(self.GetEpisodeIdFromURL(href))
        else:
            infoLabels = {u'Title': title, u'Plot': title}
            
        newListItem.setInfo(u'video', infoLabels)
    
        self.log(u"label == " + newLabel, xbmc.LOGDEBUG)
    
        if u"episodes available" in date:
            url = self.GetURLStart()  + u'&listavailable=1' + u'&page=' + mycgi.URLEscape(href)
            folder = True
        else:
            folder = False
            match = re.search( u"/player/ie/show/([0-9]+)/", href )
            if match is None:
                self.log(u"No show id found in page href: '%s'" % page, xbmc.LOGWARNING)
                return
        
            episodeId = match.group(1)
    
            url = self.GetURLStart() + u'&episodeId=' +  mycgi.URLEscape(episodeId)
    
        listItems.append( (url, newListItem, folder) )
    
    
    #==============================================================================
    
    def ListShows(self, html):
        self.log(u"", xbmc.LOGDEBUG)
        listItems = []
    
        try:
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            episodes = soup.findAll(u'a', u"thumbnail-programme-link")

            for episode in episodes:
                self.AddEpisodeToList(listItems, episode)
    
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
    
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting list of shows
            exception.addLogMessage(self.language(40100))
            # Error getting list of shows
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False
    
    
    #==============================================================================
    def GetTextFromElement(self, element):
        textList = element.contents
        text = u""
        
        for segment in textList:
            text = text + segment.string
                
        htmlparser = HTMLParser.HTMLParser()
        return htmlparser.unescape(text)    
        
        
    def AddEpisodeToSearchList(self, listItems, article):
        """
        <article class="search-result clearfix"><a
                href="/player/ie/show/10098947/" class="thumbnail-programme-link"><span
                    class="sprite thumbnail-icon-play">Watch Now</span><img class="thumbnail" alt="Watch Now"
                    src="http://img.rasset.ie/0006d29f-261.jpg"></a>
            <h3 class="search-programme-title"><a href="/player/ie/show/10098947/">Nuacht and <span class="search-highlight">News</span> with Signing</a></h3>
            <p class="search-programme-episodes"><a href="/player/ie/show/10098947/">Sun 30 Dec 2012</a></p>
            <!-- p class="search-programme-date">30/12/2012</p -->
            <p class="search-programme-description">Nuacht and <span class="search-highlight">News</span> with Signing.</p>
            <span class="sprite logo-rte-one search-channel-icon">RTÉ 1</span>
        </article>
        """

        episodeLink = article.find(u'a', u"thumbnail-programme-link")
        href = episodeLink[u'href']
    
        title = self.GetTextFromElement( article.find(u'h3', u"search-programme-title").a )
        dateShown = article.findNextSibling(u'p', u"search-programme-episodes").a.text
        description = self.GetTextFromElement( article.findNextSibling(u'p', u"search-programme-description") )
        thumbnail = article.find('img', 'thumbnail')['src']
        
        title = title + u' [' + dateShown + u']'
    
        newLabel = title
                                        
        newListItem = xbmcgui.ListItem( label=newLabel)
        infoLabels = {u'Title': title, u'Plot': description, u'PlotOutline': description}
        newListItem.setInfo(u'video', infoLabels)
        newListItem.setThumbnailImage(thumbnail)

        match = re.search( u"/player/ie/show/([0-9]+)/", href )
        if match is None:
            self.log(u"No show id found in page href: '%s'" % page, xbmc.LOGWARNING)
            return
    
        episodeId = match.group(1)
    
        url = self.GetURLStart() + u'&episodeId=' +  mycgi.URLEscape(episodeId)
    
        listItems.append( (url, newListItem, True) )
        
    #==============================================================================
    
    def ListSearchShows(self, html):
        self.log(u"", xbmc.LOGDEBUG)
        listItems = []
        
        try:
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            articles = soup.findAll(u"article", u"search-result clearfix")
        
            if len(articles) > 0:
                for article in articles:
                    self.AddEpisodeToSearchList(listItems, article)
    
                current = soup.find('li', 'dot-current')
                
                if current is not None:
                    moreResults = current.findNextSibling('li', 'dot')
                    
                    if moreResults is not None:
                        try:
                            listItems.append( self.CreateSearchItem(moreResults.a['href']) )
                        except (Exception) as exception:
                            if not isinstance(exception, LoggingException):
                                exception = LoggingException.fromException(exception)
            
                            # Not fatal, just means that we don't have the search option
                            exception.process(severity = self.logLevel(xbmc.LOGWARNING))
                
        
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
        
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
        
            # Error getting list of shows
            exception.addLogMessage(self.language(40100))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    #==============================================================================
    
    def ListAvailable(self, html):
        self.log(u"", xbmc.LOGDEBUG)
        listItems = []
    
        try:        
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            count = int(soup.find(u'meta', { u'name' : u"episodes_available"} )[u'content'])
    
            availableEpisodes = soup.findAll(u'a', u"thumbnail-programme-link")
        
            for index in range ( 0, count ):
                self.AddEpisodeToList(listItems, availableEpisodes[index])
    
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
    
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting count of available episodes
            exception.addLogMessage(self.language(40030))
            exception.process(self.language(40040), self.language(40030), self.logLevel(xbmc.LOGERROR))
            return False
    
    #==============================================================================
    
    def GetSWFPlayer(self):
        self.log(u"", xbmc.LOGDEBUG)
        
        try:
            swfPlayerGroups = self.GetStringFromURL(flashJS, u"\"(http://.+swf)", 50000)
            swfPlayer = swfPlayerGroups[0].decode('utf8')
            return swfPlayer
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
            
            # Unable to determine swfPlayer URL. Using default: %s
            exception.addLogMessage(self.language(30520) % swfDefault)
            exception.process(severity = self.logLevel(xbmc.LOGWARNING))
            return swfDefault

    """
    def GetLiveSWFPlayer(self):
        self.log(u"", xbmc.LOGDEBUG)
        
        try:
            xml = self.httpManager.GetWebPage(configUrl, 20000).decode('utf8')
            soup = BeautifulStoneSoup(xml)
            
            playerUrl = soup.find("player")['url']

            if playerUrl.find('http') == 0:
                # It's an absolute URL, do nothing.
                pass
            elif playerUrl.find('/') == 0:
                # If it's a root URL, append it to the base URL:
                playerUrl = urljoin(urlRoot, playerUrl)
            else:
                # URL is relative to config.xml 
                playerUrl = urljoin(configUrl, playerUrl)
                
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting live swf player: Using default %s
            exception.addLogMessage(self.language(40160) % swfLiveDefault)
            exception.process(severity = self.logLevel(xbmc.LOGWARNING))
            playerUrl = swfLiveDefault

        return playerUrl
    """   
    #==============================================================================

    def GetThumbnailFromEpisode(self, episodeId, soup = None):
        self.log(u"", xbmc.LOGDEBUG)

        try:
            if soup is None:
                html = self.httpManager.GetWebPage(showUrl % episodeId, 20000).decode('utf8')
                soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            
            image = soup.find(u'meta', { u'property' : u"og:image"} )[u'content']
            return image
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
            
            # Error processing web page %s
            exception.addLogMessage(self.language(40060) % (showUrl % episodeId))
            exception.process(u"Error getting thumbnail", "", self.logLevel(xbmc.LOGWARNING))
            raise exception
    

    #==============================================================================
    
    def GetEpisodeInfo(self, episodeId, soup = None):
        self.log(u"", xbmc.LOGDEBUG)
    
        try:
            if soup is None:
                html = self.httpManager.GetWebPage(showUrl % episodeId, 20000).decode('utf8')
                soup = BeautifulSoup(html, selfClosingTags=[u'img'])
    
            title = soup.find(u'meta', { u'name' : u"programme"} )[u'content']
            description = soup.find(u'meta', { u'name' : u"description"} )[u'content']
            categories = soup.find(u'meta', { u'name' : u"categories"} )[u'content']
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error processing web page %s
            exception.addLogMessage(self.language(40060) % (showUrl % episodeId))
            exception.process(u"Error getting episode information", "", self.logLevel(xbmc.LOGWARNING))
    
            # Initialise values in case they are None
            if title is None:
                title = 'Unknown ' + episodeId
                
            description = unicode(description)
            categories = unicode(categories)
        
        infoLabels = {u'Title': title, u'Plot': description, u'PlotOutline': description, u'Genre': categories}
    
        self.log(u"Title: %s" % title, xbmc.LOGDEBUG)
        self.log(u"infoLabels: %s" % infoLabels, xbmc.LOGDEBUG)
        return infoLabels
    
    #==============================================================================
    
    def PlayEpisode(self, episodeId):
        self.log(u"%s" % episodeId, xbmc.LOGDEBUG)
        
        swfPlayer = self.GetSWFPlayer()
    
        try:
            html = self.httpManager.GetWebPage(showUrl % episodeId, 20000).decode('utf8')
    
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            feedsPrefix = soup.find(u'meta', { u'name' : u"feeds-prefix"} )[u'content']
    
            infoLabels = self.GetEpisodeInfo(episodeId, soup)
            thumbnail = self.GetThumbnailFromEpisode(episodeId, soup)
    
            urlGroups = self.GetStringFromURL(feedsPrefix + episodeId, u"\"url\": \"(/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/)([a-zA-Z0-9]+/)?(.+).f4m\"", 20000)
            if urlGroups is None:
                # Log error
                self.log(u"urlGroups is None", xbmc.LOGERROR)
                return False
    
            (urlDateSegment, extraSegment, urlSegment) = urlGroups
    
            rtmpStr = u"rtmpe://fmsod.rte.ie:1935/rtevod"
            app = u"rtevod"
            swfVfy = swfPlayer
            playPath = u"mp4:%s%s/%s_512k.mp4" % (urlDateSegment, urlSegment, urlSegment)
            playURL = u"%s app=%s playpath=%s swfurl=%s swfvfy=true" % (rtmp, app, playPath, swfVfy)
    
    
            rtmpVar = rtmp.RTMP(rtmp = rtmpStr, app = app, swfVfy = swfVfy, playPath = playPath)
    
            self.log(u"(%s) playUrl: %s" % (episodeId, playURL), xbmc.LOGDEBUG)
            
            return self.PlayOrDownloadEpisode(episodeId, infoLabels, thumbnail, rtmpVar)
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error playing or downloading episode %s
            exception.addLogMessage(self.language(40120) % episodeId)
            # Error playing or downloading episode %s
            exception.process(self.language(40120) % ' ' , '', self.logLevel(xbmc.LOGERROR))
            return False
    

    def PlayLiveTV(self, html):
        self.log(u"", xbmc.LOGDEBUG)
        
        #swfPlayer = self.GetLiveSWFPlayer()
        swfPlayer = self.GetSWFPlayer()
    
        liveChannels = {
                      u'RT\xc9 One' : u'rte1',
                      u'RT\xc9 Two' : u'rte2',
                      u'RT\xc9 News Now' : u'newsnow'
                      }
        
        try:
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            liveTVInfo = soup.find('span', 'sprite live-channel-now-playing').parent
            channel = liveTVInfo.find('span').string
            programme = liveTVInfo.find('span', 'live-channel-info').next.nextSibling

            infoLabels = {u'Title': channel + u": " + programme }
            thumbnailPath = self.GetThumbnailPath((channel.replace(u'RT\xc9 ', '')).replace(' ', ''))
            
            rtmpStr = u"rtmp://fmsod.rte.ie/live/"
            app = u"live"
            swfVfy = swfPlayer
            playPath = liveChannels[channel]
    
            rtmpVar = rtmp.RTMP(rtmp = rtmpStr, app = app, swfVfy = swfVfy, playPath = playPath, live = True)
            #rtmpVar = rtmp.RTMP(rtmp = rtmpStr, app = app, playPath = playPath, live = True)
            
            self.Play(infoLabels, thumbnailPath, rtmpVar)
            
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error playing live TV
            exception.addLogMessage(self.language(40190))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False
    


    def GetEpisodeIdFromURL(self, url):
        segments = url.split(u"/")
        segments.reverse()
    
        for segment in segments:
            if segment <> u'':
                return segment
    
    
    def Play(self, infoLabels, thumbnail, rtmpVar):
        self.log (u'Play titleId: ' + infoLabels[u'Title'])
    
        listItem = xbmcgui.ListItem(infoLabels[u'Title'])
        listItem.setThumbnailImage(thumbnail)
        listItem.setInfo(u'video', infoLabels)
    
        play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        play.clear()
        play.add(rtmpVar.getPlayUrl(), listItem)
    
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)
    
    
    def PlayOrDownloadEpisode(self, episodeId, infoLabels, thumbnail, rtmpVar):
        #log ('PlayOrDownloadEpisode showId: ' + showId, xbmc.LOGDEBUG)
        #log ('PlayOrDownloadEpisode episodeId: ' + episodeId, xbmc.LOGDEBUG)
        #log ('PlayOrDownloadEpisode title: ' + title, xbmc.LOGDEBUG)
    
        action = self.GetAction(infoLabels[u'Title'])
    
        try:
            if ( action == 1 ):
                # Play
                self.Play(infoLabels, thumbnail, rtmpVar)
    
            else:
                if ( action == 0 ):
                    # Download
                    defaultFilename = self.GetDefaultFilename(infoLabels[u'Title'], episodeId)
                    self.Download(rtmpVar, defaultFilename)
    
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error playing or downloading episode %s
            exception.process(self.language(40120), u'', self.logLevel(xbmc.LOGERROR))
            return False
    
        return True
    
    #==============================================================================
    
    def GetDefaultFilename(self, title, episodeId):
        if episodeId <> u"":
            #E.g. NAME.s01e12
            return title + u"_" + episodeId
    
        return title
    
   #==============================================================================
    def GetPlayerJSURL(self, html):
        try:
            soup = BeautifulSoup(html, selfClosingTags=[u'img'])
            # E.g. <script src="http://static.rasset.ie/static/player/js/player.js?v=3"></script>
            script = soup.find(src=re.compile("player.\js\?"))
        
            playerJS = script['src']
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting player.js url: Using default %s
            exception.addLogMessage(self.language(40210) % playerJSDefault)
            exception.process(severity = self.logLevel(xbmc.LOGWARNING))
            playerJS = playerJSDefault

        return playerJS
        
        
    def GetSearchURL(self):
        try:
            rootMenuHtml = self.httpManager.GetWebPage(rootMenuUrl, 60).decode('utf8')
            playerJSUrl = self.GetPlayerJSURL(rootMenuHtml)
            html = self.httpManager.GetWebPage(playerJSUrl, 20000).decode('utf8')

            programmeSearchIndex = html.find('Programme Search')
            match=re.search("window.location.href = \'(.*?)\'", html[programmeSearchIndex:])
            searchURL = match.group(1)
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting search url: Using default %s
            exception.addLogMessage(self.language(40200) + searchUrlDefault)
            exception.process(severity = self.logLevel(xbmc.LOGWARNING))
            searchURL = searchUrlDefault

        return searchURL
        
    def DoSearchQuery( self, query = None, queryUrl = None):
        if query is not None:
            queryUrl = urlRoot + self.GetSearchURL() + mycgi.URLEscape(query)
             
        self.log(u"queryUrl: %s" % queryUrl, xbmc.LOGDEBUG)
        try:
            html = self.httpManager.GetWebPage( queryUrl, 1800 ).decode('utf8')
            if html is None or html == '':
                # Data returned from web page: %s, is: '%s'
                logException = LoggingException(logMessage = self.language(30060) % ( __SEARCH__ + mycgi.URLEscape(query), html))
    
                # Error getting web page
                logException.process(self.language(30050), u'', severity = self.logLevel(xbmc.LOGWARNING))
                return False
    
            self.ListSearchShows(html)
    
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error performing query %s
            exception.addLogMessage(self.language(40170) % query)
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False
        

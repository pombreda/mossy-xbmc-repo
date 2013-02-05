# -*- coding: utf-8 -*-
import re
from time import strftime,strptime
import time, random
import simplejson
import httplib, urllib
import pyamf
from pyamf import remoting
import codecs

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

import HTMLParser
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup

from episodelist import EpisodeList
from provider import Provider
from subprocess import Popen, PIPE, STDOUT
import fourOD_token_decoder

urlRoot = u"http://www.channel4.com"
rootMenu = u"http://ps3.channel4.com/pmlsd/tags.json?platform=ps3&uid=%d"
searchUrl = u"http://www.channel4.com/search/predictive/?q=%s"
ps3Url = u"http://ps3.channel4.com/pmlsd/%s/4od.json?platform=ps3&uid=%d" # showId, time
ps3CategoryUrl = u"http://ps3.channel4.com/pmlsd/tags/%s/4od%s%s.json?platform=ps3" # % (categoryId, /order?, /page-X? )
ps3ShowUrl = u"http://ps3.channel4.com/pmlsd/%s.json?platform=ps3&uid=" 
ps3Root = u"http://ps3.channel4.com"
swfDefault = u"http://ps3.channel4.com/swf/ps3player-9.0.124-1.27.2.swf"

class FourODProvider(Provider):

    def GetProviderId(self):
        return u"4oD"

    def ExecuteCommand(self, mycgi):
        return super(FourODProvider, self).ExecuteCommand(mycgi)
    
    def GetHeaders(self):
        # PS3
        headers = {
                   'User-Agent' : "Mozilla/5.0 (PLAYSTATION 3; 3.55)",
                   'DNT' : '1'
                   }
        return headers

    def ShowRootMenu(self):
        self.log(u"", xbmc.LOGDEBUG)
        
        try:
            jsonText = None
            jsonText = self.httpManager.GetWebPage(rootMenu % int(time.time()*1000), 338)
    
            jsonData = simplejson.loads(jsonText)
            
            listItemsAtoZ = []
    
            if isinstance(jsonData['feed']['entry'], list):
                entries = jsonData['feed']['entry']
            else:
                # Single entry, put in a list
                entries = [ jsonData['feed']['entry'] ] 
            
            #TODO Error handling?
            orderedEntries = {}
            for entry in entries:
                """
                {"link":
                    {"self":"http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals.json?platform=ps3",
                    "related":
                        ["http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals\/title.json?platform=ps3",
                        "http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals\/4od.json?platform=ps3",
                        "http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals\/4od\/title.json?platform=ps3"]
                    },
                "$":"\n    \n    \n    \n    \n    \n    \n    \n    \n    \n    \n    \n  ",
                "id":"tag:ps3.channel4.com,2009:\/programmes\/tags\/animals",
                "title":"Animals",
                "summary":
                    {"@type":"html",
                    "$":"Channel 4 Animals Programmes"
                    },
                "updated":"2013-01-29T13:34:11.491Z",
                "dc:relation.CategoryType":"None",
                "dc:relation.AllProgrammeCount":5,
                "dc:relation.4oDProgrammeCount":1
                }
                """
                if entry['dc:relation.4oDProgrammeCount'] == 0:
                    continue
                
                id = entry[u'id']
                pattern = u'/programmes/tags/(.+)'
                match = re.search(pattern, id, re.DOTALL | re.IGNORECASE)
                
                categoryName = match.group(1)
                label = entry[u'title'] + u' (' + unicode(entry['dc:relation.4oDProgrammeCount']) + u')' 
                newListItem = xbmcgui.ListItem( label=label )
                
                url = self.GetURLStart() + u'&category=' + mycgi.URLEscape(categoryName) + u'&title=' + mycgi.URLEscape(label) + u'&order=' + mycgi.URLEscape(u'/title') + u'&page=1'
                
                if 'dc:relation.CategoryOrder' in entry:
                    order = entry['dc:relation.CategoryOrder']
                    orderedEntries[order] = (url,newListItem,True)
                else:
                    listItemsAtoZ.append( (url,newListItem,True) )
            
            # Add listItems in "category" order
            listItems = []
            
            index = 0
            while len(orderedEntries) > 0:
                if index in orderedEntries:
                    listItems.append(orderedEntries[index])
                    del orderedEntries[index]
                    
                index = index + 1
            
            listItems.extend(listItemsAtoZ)
            xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
            xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
            
            return True
        except (Exception) as exception:
            exception = LoggingException.fromException(exception)

            if jsonText is not None:
                msg = "jsonText:\n\n%s\n\n" % jsonText
                exception.addLogMessage(msg)
                
            # Error processing categories
            exception.addLogMessage(self.language(30795))
            exception.process(self.language(30765), self.language(30795), severity = xbmc.LOGWARNING)
    
            return False
    

    def ParseCommand(self, mycgi):
        self.log(u"", xbmc.LOGDEBUG)

        (category, showId, episodeId, title, search, order, page) = mycgi.Params( u'category', u'show', u'ep', u'title', u'search', u'order', u'page' )

        if ( showId <> u'' and episodeId == u''):
            success = self.ShowEpisodes( showId, title )
        elif ( category <> u'' ):
            success = self.ShowCategory( category, title, order, page )
        elif ( episodeId <> u'' ):
            (episodeNumber, seriesNumber) = mycgi.Params( u'episodeNumber', u'seriesNumber' )
            success = self.PlayOrDownloadEpisode( showId, int(seriesNumber), int(episodeNumber), episodeId, title )


    #==============================================================================
    # AddExtraLinks
    #
    # Add links to 'Most Popular'. 'Latest', etc to programme listings
    #==============================================================================
    
    def AddExtraLinks(self, category, label, order, listItems):
        if order == '/title':
            newOrder = "" # Default order, latest
            newLabel = u' [' + 'Latest' + u' ' + label + u']'
            thumbnail = u'latest'
        else:
            newOrder = '/title' # Alphanumerical
            newLabel = u' [' + 'Title' + u' ' + label + u']'
            thumbnail = u'title'
            
        thumbnailPath = self.GetThumbnailPath(thumbnail)
        newListItem = xbmcgui.ListItem( label=newLabel )
        newListItem.setThumbnailImage(thumbnailPath)
        url = self.GetURLStart() + u'&category=' + mycgi.URLEscape(category) + u'&title=' + mycgi.URLEscape(label) + u'&order=' + mycgi.URLEscape(newOrder) + u'&page=1'
        listItems.append( (url,newListItem,True) )

    
    #==============================================================================
    # AddPageLink
    #
    # Add Next/Previous Page links to programme listings
    #==============================================================================
    
    def AddPageLink(self, category, order, previous, page, listItems):
        thumbnail = u'next'
        arrows = u'>>'
        if previous == True:
            thumbnail = u'previous'
            arrows = u'<<'
    
        thumbnailPath = self.GetThumbnailPath(thumbnail)
        # E.g. [Page 2] >>
        label = u'[' + self.language(30510) + u' ' + page + u'] ' + arrows
    
        newListItem = xbmcgui.ListItem( label=label )
        newListItem.setThumbnailImage(thumbnailPath)
    
        url = self.GetURLStart() + u'&category=' + mycgi.URLEscape(category) + u'&title=' + mycgi.URLEscape(label) + u'&order=' + mycgi.URLEscape(order) + u'&page=' + mycgi.URLEscape(page)
        listItems.append( (url,newListItem,True) )
    
    
    #==============================================================================
    # AddPageToListItems
    #
    # Add the shows from a particular page to the listItem array
    #==============================================================================
    
    def AddPageToListItems( self, category, label, order, page, listItems ):
        """
        {"feed":
            {"link":
                {"self":"http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals\/4od.json?platform=ps3",
                "up":"http:\/\/ps3.channel4.com\/pmlsd\/tags\/animals.json?platform=ps3"},
                "$":"\n  \n  \n  \n  \n  \n  \n  \n  \n  \n  \n  \n  \n  \n  \n",
                "id":"tag:ps3.channel4.com,2009:\/programmes\/tags\/animals\/4od",
                "title":"4oD Animals Programmes",
                "updated":"2013-01-29T15:12:58.105Z",
                "author":
                    {"$":"\n    \n  ",
                    "name":"Channel 4 Television"
                    },
                "logo":
                    {"@imageSource":"default",
                    "$":"http:\/\/cache.channel4.com\/static\/programmes\/images\/c4-atom-logo.gif"
                    },
                "fh:complete":"",
                "dc:relation.CategoryType":"None",
                "dc:relation.AllProgrammeCount":5,
                "dc:relation.4oDProgrammeCount":1,
                "dc:relation.platformClientVersion":1,
                "generator":{"@version":"1.43","$":"PMLSD"},
                "entry":
                    {"link":
                        {"self":"http:\/\/ps3.channel4.com\/pmlsd\/the-horse-hoarder.json?platform=ps3",
                        "related":["http:\/\/ps3.channel4.com\/pmlsd\/the-horse-hoarder\/4od.json?platform=ps3",
                        "http:\/\/ps3.channel4.com\/pmlsd\/the-horse-hoarder\/episode-guide.json?platform=ps3"]
                        },
                    "$":"\n    \n    \n    \n    \n    \n    \n    \n    \n    \n    \n    \n  ",
                    "id":"tag:ps3.channel4.com,2009:\/programmes\/the-horse-hoarder",
                    "title":"The Horse Hoarder",
                    "summary":
                        {"@type":"html",
                        "$":"Pensioner Clwyd Davies has accumulated 52 untamed horses, which he keeps at his home in Wrexham's suburbs"
                        },
                    "updated":"2013-01-07T12:30:53.872Z",
                    "dc:relation.sortLetter":"H",
                    "dc:date.TXDate":"2013-01-13T02:40:00.000Z",
                    "dc:relation.BrandWebSafeTitle":"the-horse-hoarder",
                    "content":
                        {"$":"\n      \n
                            ",
                        "thumbnail":
                            {"@url":"http:\/\/cache.channel4.com\/assets\/programmes\/images\/the-horse-hoarder\/ea8a20f0-2ba9-4648-8eec-d25a0fe35d3c_200x113.jpg",
                            "@height":"113",
                            "@width":"200",
                            "@imageSource":"own",
                            "@altText":"The Horse Hoarder"
                            }
                        }
                    }
                }
        }
        
        """
        try:
            pageInt = int(page)
        
            url = None
            if pageInt == 1:
                url = ps3CategoryUrl % (category, order, '')
            else:
                url = ps3CategoryUrl % (category, order, '/page-%s' % page)
                
            jsonText = None
            jsonText = self.httpManager.GetWebPage(url, 963)
    
            jsonData = simplejson.loads(jsonText)
            
            if isinstance(jsonData['feed']['entry'], list):
                entries = jsonData['feed']['entry']
            else:
                # Single entry, put in a list
                entries = [ jsonData['feed']['entry'] ] 

            for entry in entries:
                id = entry['id']
                pattern = '/programmes/(.+)'
                match = re.search(pattern, id, re.DOTALL | re.IGNORECASE)
                
                showId = match.group(1)
                thumbnail = entry['content']['thumbnail']['@url']
                progTitle = entry['title']
                progTitle = progTitle.replace( u'&amp;', u'&' )
                progTitle = progTitle.replace( u'&pound;', u'£' )
                synopsis = entry['summary']['$']
                synopsis = synopsis.replace( u'&amp;', u'&' )
                synopsis = synopsis.replace( u'&pound;', u'£' )
                
                newListItem = xbmcgui.ListItem( progTitle )
                newListItem.setThumbnailImage(thumbnail)
                newListItem.setInfo(u'video', {u'Title': progTitle, u'Plot': synopsis, u'PlotOutline': synopsis})
                url = self.GetURLStart() + u'&category=' + category + u'&show=' + mycgi.URLEscape(showId) + u'&title=' + mycgi.URLEscape(progTitle)
                listItems.append( (url,newListItem,True) )
                
            if 'next' in jsonData['feed']['link']:
                nextUrl = jsonData['feed']['link']['next']
            else:
                nextUrl = None

            return nextUrl
        
        except (Exception) as exception:
            exception = LoggingException.fromException(exception)
        
            if jsonText is not None:
                msg = "url: %s\n\n%s\n\n" % (unicode(url), jsonText)
                exception.addLogMessage(msg)
                
            # Error getting programme list web page
            exception.addLogMessage(self.language(30805))
            exception.process("", "", severity = self.logLevel(xbmc.LOGERROR))
    
            raise exception
    
    #==============================================================================
    
    
    def ShowCategory(self, category, label, order, page ):
        self.log(unicode(( category, label, order, page)), xbmc.LOGDEBUG)
    
        pageInt = int(page)
        
        listItems = []
    
        try:
            pattern = "\((\d+)\)"
            match = re.search(pattern, label, re.DOTALL | re.IGNORECASE)
            count = int(match.group(1))
        except:
            count = None
            
        if pageInt == 1 and count is None or count > 10:
            try:
                self.AddExtraLinks(category, label, order, listItems)
            except (Exception) as exception:
                exception = LoggingException.fromException(exception)
            
                # 'Error processing web page', 'Cannot show Category'
                exception.addLogMessage(self.language(30785))
                exception.process(self.language(30780), self.language(30785), severity = xbmc.LOGWARNING)
    
        paging = self.addon.getSetting( u'paging' )
    
        ###
        #paging = 'false'
        ###
        if (paging == u'true'):
            if pageInt > 1:
                self.AddPageLink(category, order, True, unicode(pageInt - 1), listItems)
    
            try:
                nextUrl = self.AddPageToListItems( category, label, order, page, listItems )
            except (Exception) as exception:
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)
            
                # 'Error processing web page', 'Cannot show Most Popular/A-Z/Latest'
                exception.addLogMessage(self.language(30780))
                exception.process(self.language(30785), self.language(30780), severity = xbmc.LOGWARNING)
            
                return False    

            if nextUrl is not None:
                nextPage = unicode(pageInt + 1)
                self.AddPageLink(category, order, False, nextPage, listItems)
        
        else:
            nextUrl = ''
            while len(listItems) < 500 and nextUrl is not None:
                try:
                    nextUrl = self.AddPageToListItems( category, label, order, page, listItems )
                    pageInt = pageInt + 1
                    page = unicode(pageInt)
                
                except (Exception) as exception:
                    if not isinstance(exception, LoggingException):
                        exception = LoggingException.fromException(exception)
            
                    # 'Cannot show category', 'Error processing web page'
                    exception.addLogMessage(self.language(30780))
                    exception.process(self.language(30785), self.language(30780), severity = self.logLevel(xbmc.LOGERROR))
                    return False
        
    
        xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
        xbmcplugin.setContent(handle=self.pluginhandle, content=u'tvshows')
        xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
    
        return None
    
    #==============================================================================
    
    def ShowEpisodes( self, showId, showTitle ):
        self.log(unicode(( showId, showTitle )), xbmc.LOGDEBUG)
        episodeList = EpisodeList(self.GetURLStart(), self.httpManager)
    
        try:
           episodeList.initialise(showId, showTitle)
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
        
            # 'Error processing web page', 'Cannot show Most Popular/A-Z/Latest'
            exception.addLogMessage(self.language(30740))
            exception.process(self.language(30735), self.language(30740), severity = self.logLevel(xbmc.LOGERROR))
        
            return False    
    
        listItems = episodeList.createListItems(mycgi)
    
        xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
        xbmcplugin.setContent(handle=self.pluginhandle, content=u'episodes')
        xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
    
        return True
        
    #==============================================================================
    
    def SetSubtitles(self, episodeId, hasSubtitles, filename = None):
        subtitle = None 
        if hasSubtitles:
            subtitle = self.httpManager.GetWebPage( u"http://ais.channel4.com/subtitles/%s" % episodeId, 40000 )
        
        self.log(u'Subtitle code: ' + unicode(self.httpManager.GetLastCode()), xbmc.LOGDEBUG )
        self.log(u'Subtitle filename: ' + unicode(filename), xbmc.LOGDEBUG)
    
        if subtitle is not None:
            self.log(u'Subtitle file length: ' + unicode(len(subtitle)), xbmc.LOGDEBUG)
    
        self.log(u'httpManager.GetLastCode(): ' + unicode(self.httpManager.GetLastCode()), xbmc.LOGDEBUG)
    
        if (subtitle is None or self.httpManager.GetLastCode() == 404 or len(subtitle) == 0):
            if hasSubtitles is True:
                self.log(u'No subtitles available', xbmc.LOGWARNING )
            subtitleFile = sys.modules["__main__"].NO_SUBTITLE_FILE
        else:
            if filename is None:
                subtitleFile = sys.modules["__main__"].SUBTITLE_FILE
            else:
                subtitleFile = filename
    
            quotedSyncMatch = re.compile(u'<Sync Start="(.*?)">', re.IGNORECASE)
            subtitle = quotedSyncMatch.sub(u'<Sync Start=\g<1>>', subtitle)
            subtitle = subtitle.replace( u'&quot;', u'"')
            subtitle = subtitle.replace( u'&apos;', u"'")
            subtitle = subtitle.replace( u'&amp;', u'&' )
            subtitle = subtitle.replace( u'&pound;', u'£' )
            subtitle = subtitle.replace( u'&lt;', u'<' )
            subtitle = subtitle.replace( u'&gt;', u'>' )
    
            filesub=codecs.open(subtitleFile, u'w', u'utf-8')
            filesub.write(subtitle)
            filesub.close()
    
        return subtitleFile
    
    #==============================================================================
    # Play
    #
    #
    #==============================================================================
    
    def Play(self, playURL, showId, episodeId, title):
        self.log (u'Play showId: ' + unicode(showId))
        self.log (u'Play episodeId: ' + unicode(episodeId))
        self.log (u'Play titleId: ' + unicode(title))
        self.log (u'Play url: ' + unicode(playURL))
    
        episodeList = EpisodeList(self.GetURLStart(), self.httpManager)
        hasSubtitles = True
        try:
            episodeList.initialise(showId, title)
            episodeDetail = episodeList.GetEpisodeDetail(episodeId)
            hasSubtitles = episodeDetail.hasSubtitles
            listItem = episodeList.createNowPlayingListItem(episodeDetail)
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
        
            exception.addLogMessage(self.language(30745))
            # "Error parsing html", "Cannot add show to \"Now Playing\"
            exception.process(self.language(30735), self.language(30745), xbmc.LOGWARNING)
        
            listItem = xbmcgui.ListItem(title)
            listItem.setInfo(u'video', {u'Title': title})
    
        play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        play.clear()
        play.add(playURL, listItem)
    
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)
    
        subtitles = self.addon.getSetting( u'subtitles' )
    
        if (subtitles == u'true'):
            try:
                subtitleFile = self.SetSubtitles(episodeId, hasSubtitles)
                xbmc.Player().setSubtitles(subtitleFile)
            except (Exception) as exception:
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)
            
                # Error getting subtitles
                exception.addLogMessage(self.language(30970))
                exception.process('', '', severity = xbmc.LOGWARNING)
                
    
    #==============================================================================
    def Download(self, rtmpvar, episodeId, defaultFilename):
        (rtmpdumpPath, downloadFolder, filename) = self.GetDownloadSettings(defaultFilename)
        
        savePath = os.path.join( downloadFolder, filename )
    
        subtitles = self.addon.getSetting( 'subtitles' )
    
        if (subtitles == u'true'):
                self.log (u"Getting subtitles")
                # Replace '.flv' or other 3 character extension with '.smi'
                self.SetSubtitles(episodeId, savePath[0:-4] + u'.smi')
    
        rtmpvar.setDownloadDetails(rtmpdumpPath, savePath)
        parameters = rtmpvar.getParameters()
        #log ("Starting download: " +  unicode(parameters))#
    
        #log ("Starting download: " + filename + " " + unicode(params))
        #log ("Download would be: " + os.path.join(params["download_path"].decode("utf-8"), filename))
            #__downloader__.download(filename, params)
            
        # Starting download
        self.log (u"Starting download: " + rtmpdumpPath + " " + unicode(parameters))
        xbmc.executebuiltin('XBMC.Notification(4oD %s, %s)' % ( self.language(30610), filename))
    
        self.log(u'"%s" %s' % (rtmpdumpPath, parameters))
        if get_system_platform() == u'windows':
            p = Popen( parameters, executable=rtmpdumpPath, shell=True, stdout=PIPE, stderr=PIPE )
        else:
            cmdline = u'"%s" %s' % (rtmpdumpPath, parameters)
            p = Popen( cmdline, shell=True, stdout=PIPE, stderr=PIPE )
    
        self.log (u"rtmpdump has started executing", xbmc.LOGDEBUG)
        (stdout, stderr) = p.communicate()
        self.log (u"rtmpdump has stopped executing", xbmc.LOGDEBUG)
    
        if u'Download complete' in stderr:
            # Download Finished!
            self.log (u'stdout: ' + unicode(stdout), xbmc.LOGDEBUG)
            self.log (u'stderr: ' + unicode(stderr), xbmc.LOGDEBUG)
            self.log (u"Download Finished!")
            xbmc.executebuiltin(u'XBMC.Notification(%s,%s,2000)' % ( self.language(30620), filename))
        else:
            # Download Failed!
            self.log (u'stdout: ' + unicode(stdout), xbmc.LOGERROR)
            self.log (u'stderr: ' + unicode(stderr), xbmc.LOGERROR)
            self.log (u"Download Failed!")
            xbmc.executebuiltin(u'XBMC.Notification(%s,%s,2000)' % ( u"Download Failed! See log for details", filename))
            
    
    #==============================================================================
    
    def GetAuthentication(self, uriData):
        token = uriData.find(u'token').string
        cdn = uriData.find(u'cdn').string
        
        self.log(u"cdn: %s" % cdn, xbmc.LOGDEBUG)
        self.log(u"token: %s" % token, xbmc.LOGDEBUG)
        decodedToken = fourOD_token_decoder.Decode4odToken(token)
    
        if ( cdn ==  u"ll" ):
            ip = uriData.find(u'ip')
            e = uriData.find(u'e')
            if (ip):
                self.log(u"ip: %s" % ip.string, xbmc.LOGDEBUG)
                auth = u"e=%s&ip=%s&h=%s" % (e.string, ip.string, decodedToken)
            else:
                auth = "e=%s&h=%s" % (e.string, decodedToken)
                
        else:
                fingerprint = uriData.find('fingerprint').string
                slist = uriData.find('slist').string
                
                auth = "auth=%s&aifp=%s&slist=%s" % (decodedToken, fingerprint, slist)
    
        self.log(u"auth: %s" % auth, xbmc.LOGDEBUG)
    
        return auth
    
    #==============================================================================
    
    def GetStreamInfo(self, assetUrl):
        maxAttempts = 10
        for attemptNumber in range(0, maxAttempts):
            xml = self.httpManager.GetWebPageDirect( assetUrl )
            
            self.log("assetUrl: %s\n\n%s\n\n" % (assetUrl, xml), xbmc.LOGDEBUG)

            soup = BeautifulStoneSoup(xml)

            uriData = soup.find(u'uridata')
            streamURI = uriData.find(u'streamuri').text

            # If HTTP Dynamic Streaming is used for this show then there will be no mp4 file,
            # and decoding the token will fail, therefore we abort before
            # parsing authentication info if there is no mp4 file.
            if u'mp4:' not in streamURI.lower():
                # Unable to find MP4 video file to play.
                # No MP4 found, probably HTTP Dynamic Streaming. Stream URI - %s
                exception.addLogMessage(self.language(30815))
                exception.process(self.language(30815), self.language(30550), severity = self.logLevel(xbmc.LOGERROR))
                raise exception
    
            auth =  self.GetAuthentication(uriData)
        
            if auth is None:
                # If we didn't get the cdn we're looking for then try again
                # Error getting correct cdn, trying again
                self.log(self.language(30955))
                continue
    
            break
    
        return (streamURI, auth)
    
    #==============================================================================
    def GetSwfPlayer(self):
        try:
            rootHtml = None
            rootHtml = self.httpManager.GetWebPage(ps3Root, 20000)

            soup = BeautifulStoneSoup(rootHtml)
            script = soup.find('script', src=re.compile('.+com.channel4.aggregated.+', re.DOTALL | re.IGNORECASE))
            jsUrl = script['src']
            
            jsHtml = None
            jsHtml = self.httpManager.GetWebPage(ps3Root + '/' + jsUrl, 20000)
            
            """
            getPlayerSwf:function(){return"swf/ps3player-9.0.124-1.27.2.swf"},
            """
            pattern = "getPlayerSwf[^\"]+\"([^\"]+)\""
            match = re.search(pattern, jsHtml, re.DOTALL | re.IGNORECASE)
            
            swfPlayer = ps3Root + '/' + match.group(1)
            
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
        
            if rootHtml is not None:
                msg = "rootHtml:\n\n%s\n\n" % rootHtml
                exception.addLogMessage(msg)
                
            if jsHtml is not None:
                msg = "jsHtml:\n\n%s\n\n" % jsHtml
                exception.addLogMessage(msg)
                
            # Unable to determine swfPlayer URL. Using default: 
            exception.addLogMessage(self.language(30520) + swfDefault)
            exception.process('', '', severity = xbmc.LOGWARNING)

            swfPlayer = swfDefault
        
        return swfPlayer



    def InitialiseRTMP(self, assetUrl):
        self.log(u'assetUrl: %s' % assetUrl, xbmc.LOGDEBUG)
    
        # Get the stream info
        (streamUri, auth) = self.GetStreamInfo(assetUrl)

        url = re.search('(.*?)mp4:', streamUri).group(1)
        app = re.search('.com/(.*?)mp4:', streamUri).group(1)
        playPath = re.search('(mp4:.*)', streamUri).group(1) + "?" + auth
        if "ll."  not in streamUri: 
            url = url + "?ovpfv=1.1&" + auth
            app = app + "?ovpfv=1.1&" + auth
        
        swfPlayer = self.GetSwfPlayer()
        rtmpvar = rtmp.RTMP(rtmp = streamUri, app = app, swfVfy = swfPlayer, playPath = playPath, pageUrl = urlRoot)
        return rtmpvar
    
    #==============================================================================
    
    def getDefaultFilename(self, showId, seriesNumber, episodeNumber):
        if ( seriesNumber <> "" and episodeNumber <> "" ):
            #E.g. NAME.s01e12
            return showId + u".s%0.2ie%0.3i" % (int(seriesNumber), int(episodeNumber))
        
        return showId
    
    def GetSeriesAndEpisode(self, entry):
        if 'dc:relation.SeriesNumber' in entry and 'dc:relation.EpisodeNumber' in entry:
            return (entry['dc:relation.SeriesNumber'], entry['dc:relation.EpisodeNumber'])
        
        pattern = u'series-([0-9]+)(\\\)?/episode-([0-9]+)'
        seasonAndEpisodeMatch = re.search( pattern, entry[u'link'][u'related'], re.DOTALL | re.IGNORECASE )

        self.log("Searching for season and episode numbers in url: %s" % entry[u'link'][u'related'], xbmc.LOGDEBUG)
        if seasonAndEpisodeMatch is not None:
            seriesNum = int(seasonAndEpisodeMatch.group(1))
            epNum = int(seasonAndEpisodeMatch.group(3))
            
            return (seriesNum, epNum)
        
        return None, None
        
    
    def GetPS3AssetUrl(self, showId, seriesNumber, episodeNumber):
        headers = {}
        headers['DNT'] = '1'
        headers['Referer'] = 'http://ps3.channel4.com'  
        headers['User-Agent'] = 'Mozilla/5.0 (PLAYSTATION 3; 3.55)' 

        url = ps3Url % (showId, int(time.time()*1000))
        data = self.httpManager.GetWebPage(url, 933)
        
        self.log("ps3Url: %s\n\n%s\n\n" % (url, data), xbmc.LOGDEBUG)
        
        jsonData = simplejson.loads(data)

        if isinstance(jsonData['feed']['entry'], list):
            entries = jsonData['feed']['entry']
        else:
            # Single entry, put in a list
            entries = [ jsonData['feed']['entry'] ] 

        for entry in entries:
            (entrySeriesNum, entryEpNum) = self.GetSeriesAndEpisode(entry)
            if entrySeriesNum is None or entryEpNum is None:
                self.log("Error determining season and episode numbers for this episide: \n\n%s\n\n" % entry, xbmc.LOGWARNING)
                continue
            
            if entrySeriesNum == seriesNumber and entryEpNum == episodeNumber:
                return entry['group']['player']['@url']

        return None

    #==============================================================================
    def getRTMPUrl(self, showId, seriesNumber, episodeNumber, episodeId):
        playUrl = None

        try:    
            assetUrl = self.GetPS3AssetUrl(showId, seriesNumber, episodeNumber)
            rtmpvar = self.InitialiseRTMP(assetUrl)
            playUrl = rtmpvar.getPlayUrl()    

            return (playUrl, rtmpvar)
    
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
        
            exception.addLogMessage(self.language(30810))
            # "Error parsing html", "Error getting stream info xml"
            exception.process(self.language(30735), self.language(30810), severity = self.logLevel(xbmc.LOGERROR))

            raise exception
    
    
    def PlayOrDownloadEpisode( self, showId, seriesNumber, episodeNumber, episodeId, title ):
        self.log (u'PlayOrDownloadEpisode showId: ' + showId, xbmc.LOGDEBUG)
        self.log (u'PlayOrDownloadEpisode episodeId: ' + episodeId, xbmc.LOGDEBUG)
        self.log (u'PlayOrDownloadEpisode title: ' + title, xbmc.LOGDEBUG)
    
        dialog = xbmcgui.DialogProgress()
        dialog.create(u'4od', u'')
    
        # 'Looking for video on 4od'
        dialog.update(0,  self.language(30885))
    
        try:
            (playUrl, rtmpvar) = self.getRTMPUrl(showId.lower(), seriesNumber, episodeNumber, episodeId)
        except (LoggingException) as exception:
            # Error getting RTMP url
            exception.addLogMessage(self.language(30965))
            exception.process("", "", severity = self.logLevel(xbmc.LOGERROR))
            
            dialog.close()
            return False
    
        if dialog.iscanceled():
            return True
    
        dialog.close()
    
        self.log (u'PlayOrDownloadEpisode: error: %s' % unicode(rtmpvar))
    
        # If we can't get rtmp then don't do anything
        if rtmpvar is None:
            return False
    
        action = self.GetAction(title)
    
        if ( action == 1 ):
            # Play
            self.Play(playUrl, showId, episodeId, title)
        
        else:
            if ( action == 0 ):
                # Download
                defaultFilename = self.getDefaultFilename(showId, seriesNumber, episodeNumber)
                self.Download(rtmpvar, episodeId, defaultFilename)
    
        return None

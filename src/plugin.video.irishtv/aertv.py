# -*- coding: utf-8 -*-
import re
from time import strftime,strptime
import time, random
import simplejson
import httplib, urllib
import pyamf
from pyamf import remoting

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

from provider import Provider

urlRoot     = u"http://www.aertv.ie"
c_brightcove = u"http://c.brightcove.com"

# Default values only used if we can't get the info from the net, e.g. GEO-BLOCKEDonly used if we can't get the info from the net, e.g. GEO-BLOCKEDonly used if we can't get the info from the net, e.g. GEO-BLOCKED
defaultRTMPUrl = u"rtmpe://85.91.5.163:1935/rtplive&" 

# RTMP stub 
channelToStream = {
                u'rte-one' : u'RTEONE_v500.stream',
                u'rte-two' : u'RTETWO_v500.stream',
                u'rte-two-hd' : u'RTETWOHD_v1500.stream',
                u'tv3' : u'TV3_v500.stream',
                u'tg4' : u'TG4_v500.stream',
                u'3e' : u'3E_v500.stream',
                u'rte-one1' : u'RTEPLUSONE_v500.stream',
                u'rte-news-now' : u'RTENEWSNOW_v500.stream',
                u'rtejr' : u'RTEJUNIOR_v500.stream'
                }

class AerTVProvider(Provider):

    def GetProviderId(self):
        return u"AerTV"

    def ExecuteCommand(self, mycgi):
        return super(AerTVProvider, self).ExecuteCommand(mycgi)

    def GetJSONPath(self):
        epochTimeMS = int(round(time.time() * 1000.0))
        # POST /?callback=jQuery18208056761118918062_1358250191844 HTTP/1.1
        callbackToken = "/?callback=jQuery1820%s_%s" % ( random.randint(3000000, 90000000000), epochTimeMS)
        return callbackToken 

    def ShowRootMenu(self):
        self.log(u"", xbmc.LOGDEBUG)
        
        try:
            url = urlRoot + self.GetJSONPath()
            values = {'source':'ddl', 'length':'24', 'type':'basic'}
            ddlJSONText = self.httpManager.GetWebPage(url, 7200, values = values).decode('utf8')
    
            ddlJSONText = utils.extractJSON (ddlJSONText)
            ddlJSON = simplejson.loads(ddlJSONText)

            epgJSON = self.GetEpgJSON(url)

            return self.ShowChannelList(url, ddlJSON, epgJSON)
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error showing root menu
            exception.addLogMessage(self.language(40070))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False

    def ParseCommand(self, mycgi):
        self.log(u"", xbmc.LOGDEBUG)
        (channel, url) = mycgi.Params( u'channel', u'url') 
       
        if channel <> '' and url <> '':
            return self.PlayChannel(channel, url)
        #    return self.PlayEpisode(episodeId.decode('utf8'))


    def ShowChannelList(self, url, ddlJSON, epgJSON):
    
        channelDetails = self.ParseEPGData(epgJSON)
        
        soup = BeautifulSoup(ddlJSON['data'])

        listItems = []

        anchors=soup.findAll('a')
        for anchor in anchors:
            try:
                playerIndex = anchor['href'].index('#') + 1
                slug = anchor['href'][playerIndex:]

                if slug in channelToStream.keys():
                    (label, description, logo) = self.GetListItemDataForSlug(channelDetails, slug)
                    newLabel = anchor.text + " " + label
                    
                    newListItem = xbmcgui.ListItem( label=newLabel )
                    newListItem.setThumbnailImage(logo)
                    channelUrl = self.GetURLStart() + u'&channel=' + slug + u'&url=' + mycgi.URLEscape(url)
                    
                    infoLabels = {'Title': newLabel, 'Plot': description, 'PlotOutline': description}
        
                    newListItem.setInfo(u'video', infoLabels)
                    listItems.append( (channelUrl, newListItem, False) )
            except (Exception) as exception:
                # Problem getting details for a particular channel, show a warning and keep going 
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)
    
                # Error processing channel 
                message = self.language(40350)
            
                try:
                    message = message + " " + anchor.text
                    message = message.encode('utf8')
                except NameError:
                    pass
                      
                exception.addLogMessage(message)
                exception.process(severity = self.logLevel(xbmc.LOGWARNING))
            

        xbmcplugin.addDirectoryItems( handle=self.pluginhandle, items=listItems )
        xbmcplugin.endOfDirectory( handle=self.pluginhandle, succeeded=True )
        
        return True

    #TODO Consider breaking the epgJSON processing into a separate class
    def ParseEPGData(self, epgJSON):
        channelDetails = {}
    
        # Using slug as the identifier for each channel, create a dictionary that allows details of each channel to be looked up by slug.
        for channelEntry in epgJSON['data']:
            slug = channelEntry['channel']['slug']
            detail = [channelEntry['channel']['logo']]
            
            # Now
            if len(channelEntry['videos']) > 0:
                detail.append(channelEntry['videos'][0])

                # Next
                if len(channelEntry['videos']) > 1:
                    detail.append(channelEntry['videos'][1])

            channelDetails[slug] = detail

        return channelDetails

    def ParseEPGDataForOneChannel(self, slug, epgJSON):
        for channelEntry in epgJSON['data']:
            if slug == channelEntry['channel']['slug']:
                detail = [channelEntry['channel']['logo']]
                
                # Now
                if len(channelEntry['videos']) > 0:
                    detail.append(channelEntry['videos'][0])
    
                    # Next
                    if len(channelEntry['videos']) > 1:
                        detail.append(channelEntry['videos'][1])
                        
                return detail
    
        return None

    def GetListItemData(self, detail):
        description = ''
        if len(detail) == 1:
            label = 'Off Air'
            self.log(repr(detail))
        else:
            description = detail[1]['description']
            label = detail[1]['name']
            if len(detail) > 2:
                # E.g. "Nuacht [18:00 Six One]"
                startTime = strptime(detail[2]['starttime'], u"%Y-%m-%dT%H:%M:%S")
                label = "   " + label + "   [  " + strftime("%H:%M", startTime) + "  " + detail[2]['name']  + "  ]"
        
        return label, description, detail[0]

        
    def GetListItemDataForSlug(self, channelDetails, slug):
        detail = channelDetails[slug]

        return self.GetListItemData(detail)
    

    def PlayChannel(self, channel, epgUrl):
        
        try:
            url = urlRoot + self.GetJSONPath()
            values = {'source':'player', 'type':'name', 'val':channel}
        
            jsonData = self.httpManager.GetWebPage(url, 20000, values = values).decode('utf8')
    
            jsonText = utils.extractJSON (jsonData)
            playerJSON=simplejson.loads(jsonText)
            self.log("json data:" + unicode(playerJSON))
            
            playerId = playerJSON['data']['playerId']
            publisherId = playerJSON['data']['publisherId']
            playerKey = playerJSON['data']['playerKey']
    
            rtmpUrl = self.GetRtmpUrl(playerKey, channel, urlRoot + '/#' + channel, playerId)

            playPathIndex = rtmpUrl.index('&') + 1
            playPath = rtmpUrl[playPathIndex:]
            swfUrl = self.get_swf_url(channel, playerId, publisherId, playerKey)
            pageUrl = urlRoot
            
            if 'videoId' in playerJSON['data']:
                videoId = playerJSON['data']['videoId']
            else:
                videoId = playerJSON['data']['offset']['videos'][0]
                
            app = "rtplive?videoId=%s&lineUpId=&pubId=%s&playerId=%s" % (videoId, publisherId, playerId)
            rtmpVar = rtmp.RTMP(rtmp = rtmpUrl, app = app, swfUrl = swfUrl, playPath = playPath, pageUrl = pageUrl, live = True)

            # Set up info for "Now Playing" screen
            infoLabels, logo = self.GetInfoLabelsAndLogo(channel, epgUrl)
            
            self.Play(infoLabels, logo, rtmpVar)            
            
            return True
       
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error preparing or playing stream
            exception.addLogMessage(self.language(40340))
            exception.process(severity = self.logLevel(xbmc.LOGERROR))
            return False


    def Play(self, infoLabels, thumbnail, rtmpVar):
        if infoLabels is None:
            self.log (u'Play titleId: Unknown Title')
            listItem = xbmcgui.ListItem(u'Unknown Title')
        else:
            self.log (u'Play titleId: ' + infoLabels[u'Title'])
            listItem = xbmcgui.ListItem(infoLabels[u'Title'])
            listItem.setInfo(u'video', infoLabels)
        
        if thumbnail is not None:
            listItem.setThumbnailImage(thumbnail)
    
        play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        play.clear()
        play.add(rtmpVar.getPlayUrl(), listItem)
    
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(play)
    
            
    def GetInfoLabelsAndLogo(self, channel, epgUrl):
        infoLabels = None
        logo = None
        
        try:
            epgJSON = self.GetEpgJSON(epgUrl)
            details = self.ParseEPGDataForOneChannel(channel, epgJSON)
            (label, description, logo) = self.GetListItemData(details)
    
            infoLabels = {u'Title': label, u'Plot': description, u'PlotOutline': description}
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            # Error getting title and logo info for %s
            exception.addLogMessage(self.language(40370) % channel)
            exception.process(severity = xbmc.LOGWARNING)

        return infoLabels, logo

        
    def GetEpgJSON(self, url):
        values = {'source':'epg', 'length':'24', 'type':'basic', 'check_account' : ''}
        epgJSONText = self.httpManager.GetWebPage(url, 300, values = values).decode('utf8')

        epgJSONText = utils.extractJSON (epgJSONText)
        epgJSON = simplejson.loads(epgJSONText)
        
        return epgJSON 
            
        
    def GetRtmpUrl(self, key, contentRefId, url, playerId):
        try:
           response = self.get_episode_info(key, contentRefId, url, playerId)
           name = response['name']
           
           if -1 != name.find('BLOCKED'):
               # Your IP seems to be BLOCKED by AerTV
               self.log(self.language(40330), xbmc.LOGWARNING)
                
           self.log("Name field: " + name)
           rtmpUrl = response['programmedContent']['videoPlayer']['mediaDTO']['FLVFullLengthURL']

        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)

            if contentRefId in channelToStream:
                rtmpUrl = defaultRTMPUrl + channelToStream[contentRefId]
    
                # Error getting rtmp url. Using default: %s
                exception.addLogMessage(self.language(40320) % rtmpUrl)
                exception.printLogMessages(severity = xbmc.LOGWARNING)
            else:
                # Error getting rtmp url.
                exception.addLogMessage(self.language(40325))
                # Cannot play video stream
                raise exception

                
        return rtmpUrl
    
    #TODO Considering breaking out these methods into a separate class
    def get_episode_info(self, key, contentRefId, url, playerId):
       envelope = self.build_amf_request(key, contentRefId, url, playerId)
    
       self.log("POST c.brightcove.com/services/messagebroker/amf?playerKey=%s" % key, xbmc.LOGDEBUG)
       self.log("Log key: %s" % repr(key), xbmc.LOGDEBUG)    

       hub_data = remoting.encode(envelope).read()

       amfData = self.httpManager.PostBinary(c_brightcove.encode("utf8"), "/services/messagebroker/amf?playerKey=" + key.encode('ascii'), hub_data, {'content-type': 'application/x-amf'})
       response = remoting.decode(amfData).bodies[0][1].body

       return response
    
    def build_amf_request(self, key, contentRefId, url, exp_id):
       self.log('ContentRefId:' + str(contentRefId) + ', ExperienceId:' + str(exp_id) + ', URL:' + url)  

       const = 'a7ef6ffbfba938b174f5044af3343163a0877c48'
       pyamf.register_class(ViewerExperienceRequest, 'com.brightcove.experience.ViewerExperienceRequest')
       pyamf.register_class(ContentOverride, 'com.brightcove.experience.ContentOverride')
       content_override = ContentOverride(contentRefId)
       viewer_exp_req = ViewerExperienceRequest(url, [content_override], int(exp_id), key)
    
       env = remoting.Envelope(amfVersion=3)
       env.bodies.append(
          (
             "/1",
             remoting.Request(
                target="com.brightcove.experience.ExperienceRuntimeFacade.getDataForExperience",
                body=[const, viewer_exp_req],
                envelope=env
             )
          )
       )
       return env

    def get_swf_url(self, videoPlayer, playerId, publisherId, playerKey):
        qsdata = {}
        qsdata['width'] = '100%'
        qsdata['height'] = '100%'
        qsdata['flashID'] = 'aertv'
        qsdata['playerID'] = playerId
        qsdata['purl'] = urlRoot
        qsdata['@videoPlayer'] = videoPlayer
        qsdata['playerKey'] = playerKey
        qsdata['publisherID'] = publisherId
        qsdata['bgcolor'] = '#FFFFFF'
        qsdata['isVid'] = 'true'
        qsdata['isUI'] = 'true'
        qsdata['autostart'] = 'true'
        qsdata['wmode'] = 'transparent'
        qsdata['localizedErrorXML'] = 'https://aertv.ie/wp-content/themes/aertv/aertv-custom-error-messages.xml'
        qsdata['templateLoadHandler'] = 'liveTemplateLoaded'
        qsdata['includeAPI'] = 'true'
        qsdata['debuggerID'] = ''
        qsdata['isUI'] = 'true'
        #qsdata['startTime'] = '1358259433367'
        url = c_brightcove + "/services/viewer/federated_f9?&" + urllib.urlencode(qsdata)
        response = self.httpManager.GetHTTPResponse(url)

        location = response.url
        base = location.split("?",1)[0]
        location = base.replace("BrightcoveBootloader.swf", "federatedVideoUI/BrightcoveBootloader.swf")
        return location
    
    
class ViewerExperienceRequest(object):
   def __init__(self, URL, contentOverrides, experienceId, playerKey, TTLToken=''):
      self.TTLToken = TTLToken
      self.URL = URL
      self.deliveryType = float(0)
      self.contentOverrides = contentOverrides
      self.experienceId = experienceId
      self.playerKey = playerKey

class ContentOverride(object):
   def __init__(self, contentRefId, contentType=0, contentRefIdtarget='videoPlayer'):
      self.contentType = contentType
      self.contentId = float(0)
      self.target = contentRefIdtarget
      self.contentIds = None
      self.contentRefId = contentRefId
      self.contentRefIds = None
      self.contentType = 0
      self.featureId = float(0)
      self.featuredRefId = None


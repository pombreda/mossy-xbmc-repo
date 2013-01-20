# -*- coding: utf-8 -*-
import os
import sys
import re

from loggingexception import LoggingException
from urlparse import urlunparse
import HTMLParser


if hasattr(sys.modules["__main__"], "xbmc"):
    xbmc = sys.modules["__main__"].xbmc
else:
    import xbmc

#from xbmc import log


if hasattr(sys.modules["__main__"], "xbmcgui"):
    xbmcgui = sys.modules["__main__"].xbmcgui
else:
    import xbmcgui

#import SimpleDownloader

from subprocess import Popen, PIPE, STDOUT
import mycgi
import utils

#__downloader__ = SimpleDownloader.SimpleDownloader()
class Provider(object):

    def __init__(self):
        if hasattr(sys.modules["__main__"], "log"):
            self.log = sys.modules["__main__"].log
        else:
            from utils import log
            self.log = log

            self.log("")

    """
    If there is exactly one parameter then we are showing a provider's root menu
    otherwise we need to look at the other parameters to see what we need to do
    """
    def ExecuteCommand(self, mycgi):
        self.log(u"mycgi.ParamCount(): " + unicode(mycgi.ParamCount()), xbmc.LOGDEBUG)
        if mycgi.ParamCount() > 1:
            return self.ParseCommand(mycgi)
            ##return True
        else:
            return self.ShowRootMenu()

    def initialise(self, httpManager, baseurl, pluginhandle):
        self.httpManager = httpManager
        self.baseurl = baseurl
        self.pluginhandle = pluginhandle
        self.addon = sys.modules[u"__main__"].addon
        self.language = sys.modules[u"__main__"].language

    def GetURLStart(self):
        return self.baseurl + u'?provider=' + self.GetProviderId()
    
    def GetProviderId(self):
        pass
    
    def ShowRootMenu(self):
        pass
    
    def ParseCommand(self, mycgi):
        pass
    
    def GetAction(self, title):
        actionSetting = self.addon.getSetting( u'select_action' ).decode('latin1')
        self.log (u"action: " + actionSetting, xbmc.LOGDEBUG)
    
        # Ask
        if ( actionSetting == self.language(30120) ):
            dialog = xbmcgui.Dialog()
            # Do you want to play or download?    
    
            action = dialog.yesno(title, self.language(30530), u'', u'', self.language(30140),  self.language(30130)) # 1=Play; 0=Download
        # Download
        elif ( actionSetting == self.language(30140) ):
            action = 0
        else:
            action = 1
    
        return action
    
    #==============================================================================
    
    def Download(self, rtmpVar, defaultFilename):
        (rtmpdumpPath, downloadFolder, filename) = self.GetDownloadSettings(defaultFilename)
    
        savePath = os.path.join( downloadFolder, filename )

    #        subtitles = __addon__.getSetting( 'subtitles' )
    #        if (subtitles == 'true'):
    #               log ("Getting subtitles")
                # Replace '.flv' or other 3 character extension with '.smi'
    #                SetSubtitles(episodeId, savePath[0:-4] + '.smi')
##        params = rtmpVar.getSimpleParameters()
##        log (u"Starting download: " + filename + " " + unicode(params))
##        log (u"Download would be: " + os.path.join(params["download_path"], filename.encode('ascii', 'ignore')))
##        __downloader__.download(filename.encode('ascii', 'ignore'), params)
##        __downloader__.download("x", params)
##        log (u"Downloader started")
#        import time 
#        time.sleep(time.sleep(60))
##        log (u"Downloader started - returning")
##        return
#        try:
#        except (LoggingException) as exception:
#            
#        try:

        rtmpVar.setDownloadDetails(rtmpdumpPath, savePath)
        parameters = rtmpVar.getParameters()
    
        # Starting downloads 
        self.log (u"Starting download: " + rtmpdumpPath + u" " + parameters)
    
        xbmc.executebuiltin(('XBMC.Notification(%s, %s)' % ( self.language(30610), filename)).encode('utf8'))
    
        self.log(u'"%s" %s' % (rtmpdumpPath, parameters))
        if sys.modules[u"__main__"].get_system_platform() == u'windows':
            p = Popen( parameters, executable=rtmpdumpPath, shell=True, stdout=PIPE, stderr=PIPE )
        else:
            cmdline = u'"%s" %s' % (rtmpdumpPath, parameters)
            p = Popen( cmdline, shell=True, stdout=PIPE, stderr=PIPE )
    
        self.log (u"rtmpdump has started executing", xbmc.LOGDEBUG)
        (stdout, stderr) = p.communicate()
        self.log (u"rtmpdump has stopped executing", xbmc.LOGDEBUG)
    
        if u'Download complete' in stderr:
            # Download Finished!
            self.log (u'stdout: ' + str(stdout), xbmc.LOGDEBUG)
            self.log (u'stderr: ' + str(stderr), xbmc.LOGDEBUG)
            self.log (u"Download Finished!")
            xbmc.executebuiltin(('XBMC.Notification(%s,%s,2000)' % ( self.language(30620), filename)).encode('utf8'))
        else:
            # Download Failed!
            self.log (u'stdout: ' + str(stdout), xbmc.LOGERROR)
            self.log (u'stderr: ' + str(stderr), xbmc.LOGERROR)
            self.log (u"Download Failed!")
            xbmc.executebuiltin(('XBMC.Notification(%s,%s,2000)' % ( u"Download Failed! See log for details", filename)).encode('utf8'))
#        except:
#            pass

    #==============================================================================
    
    def GetDownloadSettings(self, defaultFilename):
    
        # Ensure rtmpdump has been located
        rtmpdumpPath = self.addon.getSetting(u'rtmpdump_path').decode('utf8')
        if ( rtmpdumpPath is u'' ):
            dialog = xbmcgui.Dialog()
            # Download Error - You have not located your rtmpdump executable...
            dialog.ok(self.language(30560),self.language(30570),u'',u'')
            self.addon.openSettings(sys.argv[ 0 ])
            
            rtmpdumpPath = self.addon.getSetting(u'rtmpdump_path').decode('utf8')

        if ( rtmpdumpPath is u'' ):
            return
        
        # Ensure default download folder is defined
        downloadFolder = self.addon.getSetting(u'download_folder').decode('utf8')
        if downloadFolder is '':
            d = xbmcgui.Dialog()
            # Download Error - You have not set the default download folder.\n Please update the self.addon settings and try again.','','')
            d.ok(self.language(30560),self.language(30580),u'',u'')
            self.addon.openSettings(sys.argv[ 0 ])
            
            downloadFolder = self.addon.getSetting(u'download_folder').decode('utf8')

        if downloadFolder is '':
            return
        
        if ( self.addon.getSetting(u'ask_filename') == u'true' ):
            # Save programme as...
            kb = xbmc.Keyboard( defaultFilename, self.language(30590))
            kb.doModal()
            if (kb.isConfirmed()):
                filename = kb.getText().decode('utf8')
            else:
                return
        else:
            filename = defaultFilename
        
        if ( filename.endswith(u'.flv') == False ): 
            filename = filename + u'.flv'
        
        if ( self.addon.getSetting(u'ask_folder') == u'true' ):
            dialog = xbmcgui.Dialog()
            # Save to folder...
            downloadFolder = dialog.browse(  3, self.language(30600), u'files', u'', False, False, downloadFolder ).decode('utf8')

        if ( downloadFolder == u'' ):
            return
        
        #return (downloadFolder, filename)
        return (rtmpdumpPath, downloadFolder, filename)

    def logLevel(self, requestLevel):
        if self.lastPageFromCache():
            return xbmc.LOGDEBUG
        
        return requestLevel
    
    def lastPageFromCache(self):
        if self.httpManager.getGotFromCache() and self.httpManager.getGotFromCache():
            return True
        
        return False
    
    #==============================================================================
    def GetThumbnailPath(self, thumbnail):
        path = os.path.join(sys.modules[u"__main__"].MEDIA_PATH, self.GetProviderId() + '_' + utils.replace_non_alphanum(thumbnail) + '.jpg')
        
        if not os.path.exists(path):
            path = os.path.join(sys.modules[u"__main__"].MEDIA_PATH, self.GetProviderId() + '.jpg') 

        if self.log is not None:
            self.log("GetThumbnailPath: " + path, xbmc.LOGDEBUG)
        return path
    #
    def fullDecode(self, text):
        htmlparser = HTMLParser.HTMLParser()
        text = text.replace(u'&#39;', u"'" )
        text = htmlparser.unescape(text)

        mychr = chr
        myatoi = int
        list = text.split('%')
        res = [list[0]]
        myappend = res.append
        del list[0]
        for item in list:
            if item[1:2]:
                try:
                    myappend(unicode(chr(int(item[:2], 16)), 'latin1') + item[2:])
                except:
                    myappend('%' + item)
            else:
                myappend('%' + item)
        return u"".join(res)
                 
#==============================================================================
    def DoSearch(self):
        self.log("", xbmc.LOGDEBUG)
        # Search
        kb = xbmc.Keyboard( "", self.language(30500) )
        kb.doModal()
        if ( kb.isConfirmed() == False ): return
        query = kb.getText()

        return self.DoSearchQuery( query = query )

    # Download the given url and return the first string that matches the pattern
    def GetStringFromURL(self, url, pattern, maxAge = 20000):
        self.log(u"url '%s', pattern '%s'" % (url, pattern), xbmc.LOGDEBUG)
    
        try:
            data = self.httpManager.GetWebPage(url, maxAge)
    
            self.log(u"len(data): " + str(len(data)), xbmc.LOGDEBUG)
    
            return re.search(pattern, data).groups()
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error getting web page %s
            exception.addLogMessage(self.language(40050) % url)
            raise exception
    
    

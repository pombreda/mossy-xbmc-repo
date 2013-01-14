# -*- coding: utf-8 -*-
import xbmc
import sys


class RTMP:
    def __init__(self, rtmp, auth = None, app = None, playPath = None, swfUrl = None, swfVfy = None, pageUrl = None, live = None):
        if hasattr(sys.modules["__main__"], "log"):
            self.log = sys.modules["__main__"].log
        else:
            from utils import log
        
        self.rtmp = rtmp
        self.auth = auth
        self.app = app
        self.playPath = playPath
        self.swfUrl = swfUrl
        self.swfVfy = swfVfy
        self.pageUrl = pageUrl
        self.live = live
        
        self.rtmpdumpPath = None
        self.downloadFolder = None

        self.language = sys.modules["__main__"].language
    

    def setDownloadDetails(self, rtmpdumpPath, downloadFolder):
        self.rtmpdumpPath = rtmpdumpPath
        self.downloadFolder = downloadFolder
        
        self.log (u"setDownloadDetails rtmpdumpPath: %s, downloadFolder: %s" % (self.rtmpdumpPath, self.downloadFolder), xbmc.LOGDEBUG)


    def getDumpCommand(self):
        if self.rtmpdumpPath is None or self.rtmpdumpPath == '':
            # rtmpdump path is not set
            exception = Exception(self.language(40000))
            raise exception

        args = [ self.rtmpdumpPath ]

        args.append(getParameters())

        command = ' '.join(args)

        self.log(u"command: " + command, xbmc.LOGDEBUG)
        return command

    def getSimpleParameters(self):
        if self.downloadFolder is None or self.downloadFolder == '':
            # Download Folder is not set
            exception = Exception(self.language(40010))
            raise exception;

        if self.rtmp is None or self.rtmp == '':
            # rtmp url is not set
            exception = Exception(self.language(40020))
            raise exception;

        parameters = {}

        parameters["url"] = self.rtmp
        parameters["download_path"] = self.downloadFolder

        if self.auth is not None:
            parameters["auth"] = self.auth

        if self.app is not None:
            parameters["app"] = self.app

        if self.playPath is not None:
            parameters["playpath"] = self.playPath

        if self.swfUrl is not None:
            parameters["swfUrl"] = self.swfUrl

        if self.swfVfy is not None:
            parameters["swfVfy"] = self.swfVfy

        if self.pageUrl is not None:
            parameters["pageUrl"] = self.pageUrl

        if self.live is not None:
            parameters["live"] = "true"

        self.log(u"parameters: " + unicode(parameters), xbmc.LOGDEBUG)
        return parameters

    def getParameters(self):
        if self.downloadFolder is None or self.downloadFolder == '':
            # Download Folder is not set
            exception = Exception(self.language(40010))
            raise exception;

        if self.rtmp is None or self.rtmp == '':
            # rtmp url is not set
            exception = Exception(self.language(40020))
            raise exception;

        args = [ u"--rtmp", u'"%s"' % self.rtmp, u"-o", u'"%s"' % self.downloadFolder ]

        if self.auth is not None:
            args.append(u"--auth")
            args.append(u'"%s"' % self.auth)

        if self.app is not None:
            args.append(u"--app")
            args.append(u'"%s"' % self.app)

        if self.playPath is not None:
            args.append(u"--playpath")
            args.append(u'"%s"' % self.playPath)

        if self.swfUrl is not None:
            args.append(u"--swfUrl")
            args.append(u'"%s"' % self.swfUrl)

        if self.swfVfy is not None:
            args.append(u"--swfVfy")
            args.append(u'"%s"' % self.swfVfy)

        if self.pageUrl is not None:
            args.append(u"--pageUrl")
            args.append(u'"%s"' % self.pageUrl)

        if self.live is not None:
            args.append(u"--live")

        parameters = u' '.join(args)

        self.log(u"parameters: " + parameters, xbmc.LOGDEBUG)
        return parameters

    def getPlayUrl(self):
        if self.rtmp is None or self.rtmp == '':
            # rtmp url is not set
            exception = Exception(self.language(40020))
            raise exception;

        args = [u"%s" % self.rtmp]

        if self.auth is not None:
            args.append(u"auth=%s" % self.auth)

        if self.app is not None:
            args.append(u"app=%s" % self.app)

        if self.playPath is not None:
            args.append(u"playpath=%s" % self.playPath)

        if self.swfUrl is not None:
            args.append(u"swfurl=%s" % self.swfUrl)

        if self.swfVfy is not None:
            args.append(u"swfurl=%s" % self.swfVfy)
            args.append(u"swfvfy=true")

        if self.pageUrl is not None:
            args.append(u"pageurl=%s" % self.pageUrl)

        if self.live is not None:
            args.append(u"live=true")

        playURL = u' '.join(args)

        self.log(u"playURL: " + playURL, xbmc.LOGDEBUG)

        return playURL



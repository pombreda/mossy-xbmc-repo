import xbmc
from xbmc import log

import utils

__flashVer1__ = "WIN 11,2,202,243"
__flashVer2__ = "WIN\\2011,2,202,243"
__pageUrl__ = "http://www.channel4.com"


class RTMP:
	def __init__(self, rtmp, auth = None, app = None, playPath = None, swfUrl = None, swfVfy = None, pageUrl = None):
		self.rtmp = rtmp
		self.auth = auth
                self.app = app
                self.playPath = playPath
                self.swfUrl = swfUrl
                self.swfVfy = swfVfy
		self.pageUrl = pageUrl

		self.rtmpdumpPath = None
                self.savePath = None
		

	def setDownloadDetails(self, rtmpdumpPath, savePath):
                self.rtmpdumpPath = rtmpdumpPath
		self.savePath = savePath
	
		log ("setDownloadDetails rtmpdumpPath: %s, savePath: %s" % (self.rtmpdumpPath, self.savePath), xbmc.LOGDEBUG)


	def getDumpCommand(self):
		#TODO Error if not set
		args = [ self.rtmpdumpPath ]

		args.append(getParameters())

		command = ' '.join(args)

		log("command: " + command, xbmc.LOGDEBUG)
		return command

	def getParameters(self):
		#TODO Error if not set
		args = [ "--rtmp", '"%s"' % self.rtmp, "-o", '"%s"' % self.savePath ]

		if self.auth is not None:

			args.append("--auth")
			args.append('"%s"' % self.auth)

		if self.app is not None:
			args.append("--app")
			args.append('"%s"' % self.app)

		if self.playPath is not None:
			args.append("--playpath")
			args.append('"%s"' % self.playPath)

		if self.swfUrl is not None:
			args.append("--swfUrl")
			args.append('"%s"' % self.swfUrl)

		if self.swfVfy is not None:
			args.append("--swfVfy")
			args.append('"%s"' % self.swfVfy)

		if self.pageUrl is not None:
			args.append("--pageUrl")
			args.append('"%s"' % self.pageUrl)

		parameters = ' '.join(args)

		log("parameters: " + parameters, xbmc.LOGDEBUG)
		return parameters

	def getPlayUrl(self):
		args = ["%s" % self.rtmp]

		if self.auth is not None:
			args.append("auth=%s" % self.auth)

		if self.app is not None:
			args.append("app=%s" % self.app)

		if self.playPath is not None:
			args.append("playpath=%s" % self.playPath)

		if self.swfUrl is not None:
			args.append("swfurl=%s" % self.swfUrl)

		if self.swfVfy is not None:
			args.append("swfurl=%s" % self.swfVfy)
			args.append("swfvfy=true")

		if self.pageUrl is not None:
			args.append("pageurl=%s" % self.pageUrl)

		playURL = ' '.join(args)

		log("playURL: " + playURL, xbmc.LOGDEBUG)

		return playURL

	


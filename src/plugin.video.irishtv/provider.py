# -*- coding: utf-8 -*-
import os
import sys

import xbmc
import xbmcgui
from xbmc import log

import mycgi

class Provider(object):

#	def __init__(self):

	# If there is exactly one parameter then we are showing a provider's root menu
	# otherwise we need to look at the other parameters to see what we need to do
#	def ExecuteCommand(self, mycgi, cache):
	def ExecuteCommand(self, mycgi):
		log("mycgi.ParamCount(): " + str(mycgi.ParamCount()), xbmc.LOGDEBUG)
		if mycgi.ParamCount() > 1:
			return self.ParseCommand(mycgi)
		else:
			return self.ShowRootMenu()

	def initialise(self, cache, baseurl, pluginhandle):
		self.cache = cache
		self.baseurl = baseurl
		self.pluginhandle = pluginhandle
		self.addon = sys.modules["__main__"].__addon__
		self.language = sys.modules["__main__"].__language__

	def GetURLStart(self):
		return self.baseurl + '?provider=' + mycgi.URLEscape(self.GetProviderId())

	def GetProviderId(self):
		pass

	def ShowRootMenu(self):
		pass

	def ParseCommand(self, mycgi):
		pass

	def GetAction(self, title):
		actionSetting = self.addon.getSetting( 'select_action' )
		log ("action: " + actionSetting, xbmc.LOGDEBUG)

		# Ask
		if ( actionSetting == self.language(30120) ):
			dialog = xbmcgui.Dialog()
			# Do you want to play or download?	

			action = dialog.yesno(title, self.language(30530), '', '', self.language(30140),  self.language(30130)) # 1=Play; 0=Download
		# Download
		elif ( actionSetting == self.language(30140) ):
			action = 0
		else:
			action = 1

		return action

#==============================================================================

	def Download(self, rtmpvar, episodeId, defaultFilename):
		(rtmpdumpPath, downloadFolder, filename) = self.GetDownloadSettings(defaultFilename)
	
		savePath = os.path.join( downloadFolder, filename )

	#        subtitles = __addon__.getSetting( 'subtitles' )

	#        if (subtitles == 'true'):
	#               log ("Getting subtitles")
		        # Replace '.flv' or other 3 character extension with '.smi'
	#                SetSubtitles(episodeId, savePath[0:-4] + '.smi')

		rtmpvar.setDownloadDetails(rtmpdumpPath, savePath)
		parameters = rtmpvar.getParameters()

		from subprocess import Popen, PIPE, STDOUT
		
		# Starting download
		log ("Starting download: " + rtmpdumpPath + " " + str(parameters))
		xbmc.executebuiltin('XBMC.Notification(4oD %s, %s)' % ( self.language(30610), filename))

		log('"%s" %s' % (rtmpdumpPath, parameters))
		if sys.modules["__main__"].get_system_platform() == 'windows':
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
			xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( self.language(30620), filename))
		else:
			# Download Failed!
			log ('stdout: ' + str(stdout), xbmc.LOGERROR)
			log ('stderr: ' + str(stderr), xbmc.LOGERROR)
			log ("Download Failed!")
			xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( "Download Failed! See log for details", filename))
		
#==============================================================================

	def GetDownloadSettings(self, defaultFilename):
	
		# Ensure rtmpdump has been located
		rtmpdumpPath = self.addon.getSetting('rtmpdump_path')
		if ( rtmpdumpPath is '' ):
			dialog = xbmcgui.Dialog()
			# Download Error - You have not located your rtmpdump executable...
			dialog.ok(self.language(30560),self.language(30570),'','')
			self.addon.openSettings(sys.argv[ 0 ])
	
			rtmpdumpPath = self.addon.getSetting('rtmpdump_path')
			if ( rtmpdumpPath is '' ):
				return
		
		# Ensure default download folder is defined
		downloadFolder = self.addon.getSetting('download_folder')
		if downloadFolder is '':
			d = xbmcgui.Dialog()
			# Download Error - You have not set the default download folder.\n Please update the self.addon settings and try again.','','')
			d.ok(self.language(30560),self.language(30580),'','')
			self.addon.openSettings(sys.argv[ 0 ])

			downloadFolder = self.addon.getSetting('download_folder')
			if downloadFolder is '':
				return
		
		if ( self.addon.getSetting('ask_filename') == 'true' ):
			# Save programme as...
			kb = xbmc.Keyboard( defaultFilename, self.language(30590))
			kb.doModal()
			if (kb.isConfirmed()):
				filename = kb.getText()
			else:
				return
		else:
			filename = defaultFilename
	
		if ( filename.endswith('.flv') == False ): 
			filename = filename + '.flv'
	
		if ( self.addon.getSetting('ask_folder') == 'true' ):
			dialog = xbmcgui.Dialog()
			# Save to folder...
			downloadFolder = dialog.browse(  3, self.language(30600), 'files', '', False, False, downloadFolder )
			if ( downloadFolder == '' ):
				return

		#return (downloadFolder, filename)
		return (rtmpdumpPath, downloadFolder, filename)





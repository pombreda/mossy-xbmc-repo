import xbmc
import xbmcgui

from xbmc import log


class LoggingException (Exception):
	
	def __init__(self, method, logMessage = None):
		self.logMessages = []

		if not logMessage == None:
			self.addLogMessage(method, logMessage)

	def setSeverity(self, severity):
		self.severity = severity

	def getSeverity(self):
		return self.severity

	def addLogMessage(self, method, logMessage):
		self.logMessages.append('In ' + method + ': ' + logMessage)

	def printLogMessages(self, severity):
		for message in self.logMessages:
			log(message, severity)

	def showInfo(self, messageHeading, messageDetail, severity):
		if severity == xbmc.LOGERROR:
			dialog = xbmcgui.Dialog()
			dialog.ok(messageHeading, messageDetail, 'See log for details')
		elif severity == xbmc.LOGWARNING:
			# See log for details
			xbmc.executebuiltin('XBMC.Notification(IrishTV %s, %s)' % (messageHeading, 'See log for details'))

	def process(self, messageHeading, messageDetail, severity):
		self.printLogMessages(severity)
		self.showInfo(messageHeading, messageDetail, severity)
		
	



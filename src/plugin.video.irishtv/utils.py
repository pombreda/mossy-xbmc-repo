import os
import re
import urllib2
import sys

from urlparse import urlunparse

from time import mktime,strptime

import xbmc
from xbmc import log
from xbmcaddon import Addon

	
#==============================================================================
# GetThumbnailPath
#
# Convert local file path to URI to workaround delay in showing 
# thumbnails in Banner view
#==============================================================================
def GetThumbnailPath(thumbnail):
	RESOURCE_PATH = os.path.join( sys.modules["__main__"].__addon__.getAddonInfo( "path" ), "resources" )
	MEDIA_PATH = os.path.join( RESOURCE_PATH, "media" )

	if sys.modules["__main__"].get_system_platform() == "linux":
		return urlunparse(('file', '/', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))

#	return os.path.join(MEDIA_PATH, thumbnail + '.jpg')
	return urlunparse(('file', '', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))
#


__Aug12__ = mktime(strptime("12 Aug 2012", "%d %b %Y"))

# Return true if date is later than 12 Aug 2012
def isRecentDate(dateString):
	try:
		dateCompare = mktime(strptime(dateString, "%d %b %Y"))

		if dateCompare > __Aug12__:
			return True

	except ( Exception ) as e:
		if dateString is None:
			dateString = 'None'

		xbmc.log ( 'Exception: ' + str(e) + ', dateString: ' + str(dateString), xbmc.LOGERROR )

	return False

def findString(method, pattern, string, flags = (re.DOTALL | re.IGNORECASE)):
	match = re.search( pattern, string, flags )
	#match = None ###
	if match is not None:
		return (match.group(1), None)

	# Limit logging of string to 1000 chars
	limit = 1000
	# Can't find pattern in string
	messageLog = "\nPattern - \n%s\n\nString - \n%s\n\n" % (pattern, string[0:limit])

	return (None, ErrorHandler(method, ErrorCodes.CANT_FIND_PATTERN_IN_STRING, messageLog))



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






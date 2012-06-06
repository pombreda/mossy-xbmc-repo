#/bin/python
# -*- coding: utf-8 -*-

import os
import xbmcplugin
import xbmcgui
import re
import geturllib
import fourOD_token_decoder
import mycgi
import urllib2

from urlparse import urlunparse
from xbmcaddon import Addon

__PluginName__  = 'plugin.video.4od'
__PluginHandle__ = int(sys.argv[1])
__BaseURL__ = sys.argv[0]

__settings__ = Addon(__PluginName__)
__language__ = __settings__.getLocalizedString

# Only used if we fail to parse the URL from the website
__SwfPlayerDefault__ = 'http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer_am2.1.swf'

RESOURCE_PATH = os.path.join( __settings__.getAddonInfo( "path" ), "resources" )
MEDIA_PATH = os.path.join( RESOURCE_PATH, "media" )

# Use masterprofile rather profile, because we are caching data that may be used by more than one user on the machine
DATA_FOLDER      = xbmc.translatePath( os.path.join( "special://masterprofile","addon_data", __PluginName__ ) )
CACHE_FOLDER     = os.path.join( DATA_FOLDER, 'cache' )
SUBTITLE_FILE    = os.path.join( DATA_FOLDER, 'subtitle.smi' )
NO_SUBTITLE_FILE = os.path.join( RESOURCE_PATH, 'nosubtitles.smi' )

xbmc.log("xXXSub: " + SUBTITLE_FILE)
xbmc.log("No Sub: " + NO_SUBTITLE_FILE)

class RTMP:
	def __init__(self):
		self.url = None
		self.auth = None
                self.app = None
                self.playPath = None
                self.swfPlayer = None

		self.rtmpdumpPath = None
                self.savePath = None

	def setDetailsFromURI(self, streamURI, auth, swfPlayer):
		xbmc.log('setDetailsFromURI swfPlayer: ' + swfPlayer)
		self.url = re.search( '(.*?)mp4:', streamURI, re.DOTALL ).groups()[0]
		self.url = self.url.replace( '.com/', '.com:1935/' )
		#self.url = self.url + "?ovpfv=1.1&" + auth

		self.app = re.search( '.com/(.*?)mp4:', streamURI, re.DOTALL ).groups()[0]
		self.app = self.app + "?ovpfv=1.1&" + auth

		self.playPath = re.search( '(mp4:.*)', streamURI, re.DOTALL ).groups()[0]
		self.playPath = self.playPath + '?' + auth

		self.swfPlayer = swfPlayer
		self.auth = auth

		xbmc.log ("url: " + self.url)
		xbmc.log ("app: " + self.app)

	def setDownloadDetails(self, rtmpdumpPath, savePath):
                self.rtmpdumpPath = rtmpdumpPath
                self.savePath = savePath
	
	def setProxy(self, proxy):
                self.proxy = proxy

	def getDownloadCommand(self):
		args = [
			'"%s"' % self.rtmpdumpPath,
			"--rtmp", '"%s"' % self.url,
			"--app", '"%s"' % self.app,
			#"--flashVer", '"WIN 10,3,183,7"',
			"--flashVer", '"WIN 11,0,1,152"',
			"--swfVfy", '"%s"' % self.swfPlayer,
			#"--pageUrl xxxxxx",
			"--conn", "Z:",
			"--playpath", '"%s"' % self.playPath,
			"-o", '"%s"' % self.savePath
			]

		if self.proxy is not None:
			args.append("--socks")
			args.append('"%s"' % self.proxy)

		command = ' '.join(args)
		xbmc.log("command: " + command)
		return command


	def runDownloadCommand(self):
		command = getDownloadCommand()
		# Starting download
		xbmc.executebuiltin('XBMC.Notification(4oD,%s: %s)' % ( __language__(30610), filename))
		p = Popen( cmdline, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT )
		x = p.stdout.read()
		import time 
		while p.poll() == None:
			time.sleep(2)
		x = p.stdout.read()

		# Download Finished!
		xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( __language__(30620), filename))
				

	def getPlayUrl(self):
		socks=''

		if self.proxy is not None:
			socks=' socks=' + self.proxy

		playURL = "%s?ovpfv=1.1&%s playpath=%s swfurl=%s swfvfy=true%s" % (self.url,self.auth,self.playPath,self.swfPlayer,socks)

		return playURL
	

#==============================================================================
# ShowCategories
#
# List the programme categories, retaining the 4oD order
#==============================================================================

def ShowCategories():
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/4od", 200000, GetUrlLibProxies() ) # ~2 days
	html = re.findall( '<ol class="display-cats">(.*?)</div>', html, re.DOTALL )[0]
	categories = re.findall( '<a href="/programmes/tags/(.*?)/4od">(.*?)</a>', html, re.DOTALL )
	
	listItems = []
	# Start with a Search entry	'Search'
	newListItem = xbmcgui.ListItem( __language__(30500) )
	url = __BaseURL__ + '?search=1'
	listItems.append( (url,newListItem,True) )
	for categoryInfo in categories:
		label = remove_extra_spaces(remove_html_tags(categoryInfo[1]))
		newListItem = xbmcgui.ListItem( label=label )
		url = __BaseURL__ + '?category=' + mycgi.URLEscape(categoryInfo[0]) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape('/title') + '&page=' + mycgi.URLEscape('1')
		listItems.append( (url,newListItem,True) )
	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )
		

#==============================================================================
# GetThumbnailPath
#
# Convert local file path to URI to workaround delay in showing 
# thumbnails in Banner view
#==============================================================================

def GetThumbnailPath(thumbnail):
	return os.path.join(MEDIA_PATH, thumbnail + '.jpg')
#	return urlunparse(('file', '/', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))
#	return urlunparse(('file', '', os.path.join(MEDIA_PATH, thumbnail + '.jpg'), '', '', ''))
#

#==============================================================================
# AddExtraLinks
#
# Add links to 'Most Popular'. 'Latest', etc to programme listings
#==============================================================================

def AddExtraLinks(category, label, order, listItems):
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/%s/4od%s" % (category, order), 40000, GetUrlLibProxies() ) # ~12 hrs

	extraInfos = re.findall( '<a href="/programmes/tags/%s/4od(.*?)">(.*?)</a>' % (category) , html, re.DOTALL )


	for extraInfo in extraInfos:
		if extraInfo[1] == 'Show More':
			continue

		newOrder = extraInfo[0]

		thumbnail = extraInfo[0]
		if thumbnail == '':
			thumbnail = 'latest'
		else:
			thumbnail = remove_leading_slash(thumbnail)

		thumbnailPath = GetThumbnailPath(thumbnail)
		newLabel = ' [' + extraInfo[1] + ' ' + remove_extra_spaces(remove_brackets(label))+ ']'
		newListItem = xbmcgui.ListItem( label=newLabel )
		newListItem.setThumbnailImage(thumbnailPath)

		url = __BaseURL__ + '?category=' + mycgi.URLEscape(category) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape(newOrder) + '&page=' + mycgi.URLEscape('1')
		listItems.append( (url,newListItem,True) )


#==============================================================================
# AddPageLink
#
# Add Next/Previous Page links to programme listings
#==============================================================================

def AddPageLink(category, order, previous, page, listItems):
	thumbnail = 'next'
	arrows = '>>'
	if previous == True:
		thumbnail = 'previous'
		arrows = '<<'

	thumbnailPath = GetThumbnailPath(thumbnail)
	# E.g. [Page 2] >>
	label = '[' + __language__(30510) + ' ' + page + '] ' + arrows

	newListItem = xbmcgui.ListItem( label=label )
	newListItem.setThumbnailImage(thumbnailPath)

	url = __BaseURL__ + '?category=' + mycgi.URLEscape(category) + '&title=' + mycgi.URLEscape(label) + '&order=' + mycgi.URLEscape(order) + '&page=' + mycgi.URLEscape(page)
	listItems.append( (url,newListItem,True) )


#==============================================================================

def AddPageToListItems( category, label, order, page, listItems ):
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/%s/4od%s/brand-list/page-%s" % (category, order, page), 40000, GetUrlLibProxies() ) # ~12 hrs
	showsInfo = re.findall( '<li.*?<a class=".*?" href="/programmes/(.*?)/4od".*?<img src="(.*?)".*?<p class="title">(.*?)</p>.*?<p class="synopsis">(.*?)</p>', html, re.DOTALL )

	for showInfo in showsInfo:
		showId = showInfo[0]
		thumbnail = "http://www.channel4.com" + showInfo[1]
		progTitle = showInfo[2]
		progTitle = progTitle.replace( '&amp;', '&' )
		synopsis = showInfo[3].strip()
		synopsis = synopsis.replace( '&amp;', '&' )
		synopsis = synopsis.replace( '&pound;', '£' )
		
		newListItem = xbmcgui.ListItem( progTitle )
		newListItem.setThumbnailImage(thumbnail)
		newListItem.setInfo('video', {'Title': progTitle, 'Plot': synopsis, 'PlotOutline': synopsis})
		#url = __BaseURL__ + '?category=' + category + '&show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(progTitle) + '&page=' + mycgi.URLEscape('1')
		url = __BaseURL__ + '?category=' + category + '&show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(progTitle)
		listItems.append( (url,newListItem,True) )

	nextUrl = re.search( '<ol class="promo-container" data-nexturl="(.*?)"', html, re.DOTALL ).groups()[0]

	return nextUrl


#==============================================================================


def ShowCategory( category, label, order, page ):
	listItems = []

	pageInt = int(page)
	if pageInt == 1:
		AddExtraLinks(category, label, order, listItems)

	paging = __settings__.getSetting( 'paging' )

	if (paging == 'true'):
		if pageInt > 1:
			AddPageLink(category, order, True, str(pageInt - 1), listItems)

		nextUrl = AddPageToListItems( category, label, order, page, listItems )

		if (nextUrl <> 'endofresults'):
			nextPage = str(pageInt + 1)
			AddPageLink(category, order, False, nextPage, listItems)

	else:
		nextUrl = ''
		while len(listItems) < 500 and nextUrl <> 'endofresults':
			nextUrl = AddPageToListItems( category, label, order, page, listItems )
			pageInt = pageInt + 1
			page = str(pageInt)
			


	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='tvshows')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )


#==============================================================================


def GetSwfPlayer( html ):
	try:
		swfRoot = re.search( 'var swfRoot = \'(.*?)\'', html, re.DOTALL ).groups()[0]
		fourodPlayerFile = re.search( 'var fourodPlayerFile = \'(.*?)\'', html, re.DOTALL ).groups()[0]

		#TODO Find out how to get the "asset/flash/swf/" part dynamically
		swfPlayer = "http://www.channel4.com" + swfRoot + "asset/flash/swf/" + fourodPlayerFile

		# Resolve redirect, if any
		req = urllib2.Request(swfPlayer)
		res = urllib2.urlopen(req)
		swfPlayer = res.geturl()
	except Exception, e:
		print e
		# "WARNING Unable to determine swfPlayer URL. Using default: "
		print __language__(30520) + __SwfPlayerDefault__
		swfPlayer = __SwfPlayerDefault__
	
	return swfPlayer

#==============================================================================

def GetEpisodeDetails(listItem):
	dataKeyValues = re.findall('data-([a-zA-Z\-]*?)="(.*?)"', listItem, re.DOTALL)
	values = []
	epNum=''
	assetId=''
	url=''
	image=''
	premieredDate=''
	progTitle=''
	epTitle=''
	description=''
	seriesNum=''

	for dataKeyValue in dataKeyValues:
		if (dataKeyValue[0] == 'episode-number'):
			epNum=dataKeyValue[1]
		if (dataKeyValue[0] == 'assetid'):
			assetId=dataKeyValue[1]
		if (re.search('episode[Uu]rl', dataKeyValue[0]) ):
			url=dataKeyValue[1]
		if (dataKeyValue[0] == 'image-url'):
			image=dataKeyValue[1]
		if (re.search('tx[Dd]ate', dataKeyValue[0]) ):
			premieredDate=dataKeyValue[1]
		if (re.search('episode[Tt]itle', dataKeyValue[0]) ):
			progTitle=dataKeyValue[1]
		if (re.search('episode[Ii]nfo', dataKeyValue[0]) ):
			epTitle=dataKeyValue[1]
		if (re.search('episode[Ss]ynopsis', dataKeyValue[0]) ):
			description=dataKeyValue[1]
		if (dataKeyValue[0] == 'series-number'):
			seriesNum=dataKeyValue[1]

	return (epNum, assetId, url, image, premieredDate, progTitle, epTitle, description, seriesNum)


#==============================================================================

def GetProxy():
    proxy_server = None
    proxy_port = None

    try:
	proxy_use = __settings__.getSetting('proxy_use')

	if proxy_use == 'true':
	        proxy_server = __settings__.getSetting('proxy_server')
	        proxy_port = int(__settings__.getSetting('proxy_port'))
    except:
        pass

    xbmc.log (str(proxy_use) + ' , ' + proxy_server + ', ' + str(proxy_port))
    
    if proxy_server is None or proxy_server == '' or proxy_port is None or proxy_port == '':
	return None

    return '%s:%s' % (proxy_server, proxy_port)

#==============================================================================

def ShowEpisodes( showId, showTitle ):
	html = geturllib.GetURL( "http://www.channel4.com/programmes/" + showId + "/4od", 20000, GetUrlLibProxies() ) # ~6 hrs

	swfPlayer = GetSwfPlayer( html )	
	
	genre = re.search( '<meta name="primaryBrandCategory" content="(.*?)"/>', html, re.DOTALL ).groups()[0]
	ol = re.search( '<ol class="all-series">(.*?)</div>', html, re.DOTALL ).groups()[0]

	listItemsHtml = re.findall( '<li(.*?[^p])>', ol, re.DOTALL )

	listItems = []
	epsDict = dict()
	for listItemHtml in listItemsHtml:
		(epNum, assetId, url, image, premieredDate, progTitle, epTitle, description, seriesNum) = GetEpisodeDetails(listItemHtml)
		
		if (assetId == ''):
			continue;

		try: epNumInt = int(epNum)
		except: epNumInt = ""
		if ( seriesNum <> "" and epNum <> "" ):
			fn = showId + ".s%0.2ie%0.2i" % (int(seriesNum),int(epNum))
		else:
			fn = showId
		
		if ( not assetId in epsDict ):
			epsDict[assetId] = 1
			
			progTitle = progTitle.strip()
			progTitle = progTitle.replace( '&amp;', '&' )
			epTitle = epTitle.strip()
			if ( progTitle == showTitle and epTitle <> "" ):
				label = epTitle
			else:
				label = progTitle
			if len(premieredDate) > 0:
				label = label + '  [' + premieredDate + ']'
			url = "http://www.channel4.com" + url
			description = remove_extra_spaces(remove_html_tags(description))
			description = description.replace( '&amp;', '&' )
			description = description.replace( '&pound;', '£' )
			description = description.replace( '&quot;', "'" )
			if (image == ""):
				thumbnail = re.search( '<meta property="og:image" content="(.*?)"', html, re.DOTALL ).groups()[0]
			else:
				thumbnail = "http://www.channel4.com" + image
			
			newListItem = xbmcgui.ListItem( label )
			newListItem.setThumbnailImage(thumbnail)
			newListItem.setInfo('video', {'Title': label, 'Plot': description, 'PlotOutline': description, 'Genre': genre, 'premiered': premieredDate, 'Episode': epNumInt})
			url = __BaseURL__ + '?ep=' + mycgi.URLEscape(assetId) + "&title=" + mycgi.URLEscape(label) + "&fn=" + mycgi.URLEscape(fn) + "&swfPlayer=" + mycgi.URLEscape(swfPlayer) 
			listItems.append( (url,newListItem,False) )
	
	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='episodes')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )

#==============================================================================

def SetSubtitles(episodeId):
	subtitle = geturllib.GetURL( "http://ais.channel4.com/subtitles/%s" % episodeId, 0 )
	
	xbmc.log('Subtitle code: ' + str(geturllib.GetLastCode()) )

	if (geturllib.GetLastCode() == 404):
		subtitleFile = NO_SUBTITLE_FILE
	else:
		subtitleFile = SUBTITLE_FILE

		subtitle=re.sub('<Sync Start="(.*?)">', '<Sync Start=\g<1>>', subtitle)
		subtitle = subtitle.replace( '&quot;', '"')
		subtitle = subtitle.replace( '&amp;', '&' )
		subtitle = subtitle.replace( '&pound;', '£' )

		filesub=open(subtitleFile, 'w')
		filesub.write(subtitle)
		filesub.close()

	xbmc.Player().setSubtitles(subtitleFile)


#==============================================================================

def GetDownloadSettings(defaultFilename):
	# Ensure rtmpdump has been located
	rtmpdumpPath = __settings__.getSetting('rtmpdump_path')
	if ( rtmpdumpPath is '' ):
		dialog = xbmcgui.Dialog()
		# Download Error - You have not located your rtmpdump executable...
		dialog.ok(__language__(30560),__language__(30570),'','')
		__settings__.openSettings(sys.argv[ 0 ])
		return
		
	# Ensure default download folder is defined
	downloadFolder = __settings__.getSetting('download_folder')
	if downloadFolder is '':
		d = xbmcgui.Dialog()
		# Download Error - You have not set the default download folder.\n Please update the addon settings and try again.','','')
		d.ok(__language__(30560),__language__(30580),'','')
		__settings__.openSettings(sys.argv[ 0 ])
		return
		
	if ( __settings__.getSetting('ask_filename') == 'true' ):
		# Save programme as...
		kb = xbmc.Keyboard( defaultFilename, __language__(30590))
		kb.doModal()
		if (kb.isConfirmed()):
			filename = kb.getText()
		else:
			return
	else:
		filename = defaultFilename
	
	if ( filename.endswith('.flv') == False ): 
		filename = filename + '.flv'
	
	if ( __settings__.getSetting('ask_folder') == 'true' ):
		dialog = xbmcgui.Dialog()
		# Save to folder...
		downloadFolder = dialog.browse(  3, __language__(30600), 'files', '', False, False, downloadFolder )
		if ( downloadFolder == '' ):
			return

	return (rtmpdumpPath, downloadFolder, filename)


#==============================================================================

def Play(rtmp, title):
	playURL = rtmp.getPlayUrl()		
	listItem = xbmcgui.ListItem(title)
	listItem.setInfo('video', {'Title': title})
		
	xbmc.log ("playURL: " + playURL)
	xbmc.Player().play( playURL, listItem )


#==============================================================================

def Download(rtmp, defaultFilename):
	(rtmpdumpPath, downloadFolder, filename) = GetDownloadSettings(defaultFilename)
				
	savePath = os.path.join( downloadFolder, filename )

	rtmp.setDownloadDetails(rtmpdumpPath, savePath)
		
	cmdline = rtmp.getDownloadCommand()

	from subprocess import Popen, PIPE, STDOUT
		
	# Starting download
	xbmc.executebuiltin('XBMC.Notification(4oD,%s: %s)' % ( __language__(30610), filename))
	p = Popen( cmdline, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT )
	x = p.stdout.read()
	import time 
	while p.poll() == None:
		time.sleep(2)
		x = p.stdout.read()

	# Download Finished!
	xbmc.executebuiltin('XBMC.Notification(%s,%s,2000)' % ( __language__(30620), filename))

#==============================================================================

def GetAuthentication(uriData):
	token = re.search( '<token>(.*?)</token>', uriData, re.DOTALL).groups()[0]
	cdn = re.search( '<cdn>(.*?)</cdn>', uriData, re.DOTALL).groups()[0]
	decodedToken = fourOD_token_decoder.Decode4odToken(token)

	if ( cdn ==  "ll" ):
		e = re.search( '<e>(.*?)</e>', uriData, re.DOTALL ).groups()[0]
		ip = re.search( '<ip>(.*?)</ip>', uriData, re.DOTALL )
		if (ip):
			auth = "e=%s&ip=%s&h=%s" % (e,ip.groups()[0],decodedToken)
		else:
			auth = "e=%s&h=%s" % (e,decodedToken)
	else:
		fingerprint = re.search( '<fingerprint>(.*?)</fingerprint>', uriData, re.DOTALL ).groups()[0]
		slist = re.search( '<slist>(.*?)</slist>', uriData, re.DOTALL ).groups()[0]
		auth = "auth=%s&aifp=%s&slist=%s" % (decodedToken,fingerprint,slist)

	return auth
	

#==============================================================================

def GetStreamInfo(episodeId):
	xml = geturllib.GetURL( "http://ais.channel4.com/asset/%s" % episodeId, 0, GetUrlLibProxies() )
	uriData = re.search( '<uriData>(.*?)</uriData>', xml, re.DOTALL).groups()[0]
	streamURI = re.search( '<streamUri>(.*?)</streamUri>', uriData, re.DOTALL).groups()[0]

	# If f4m is used for this show then there will be no mp4 file,
	# and decoding the token will fail, therefore we abort before
	# parsing authentication info if there is no mp4 file.
	playpathSearch = re.search( '(mp4:.*)', streamURI, re.DOTALL )
	if playpathSearch is None:
		dialog = xbmcgui.Dialog()
		dialog.ok(__language__(30540),__language__(30550),'','')
		return (None, None)

	auth =  GetAuthentication(uriData)

	return (streamURI, auth)

#==============================================================================

def GetAction():
	actionSetting = __settings__.getSetting( 'select_action' )
	# Ask
	if ( actionSetting == __language__(30120) ):
		dialog = xbmcgui.Dialog()
		# Do you want to play or download?	
		action = dialog.yesno(title, __language__(30530), '', '', __language__(30140),  __language__(30130)) # 1=Play; 0=Download
	# Download
	elif ( actionSetting == __language__(30140) ):
		action = 0
	else:
		action = 1

	return action

#==============================================================================

def InitializeRTMP(episodeId, swfPlayer):
	# Get the stream info
	(streamUri, auth) = GetStreamInfo(episodeId)

	rtmp = RTMP()
	rtmp.setDetailsFromURI(streamUri, auth, swfPlayer)

	proxy=GetProxy()
	
	if proxy is not None:
		rtmp.setProxy(proxy)

	return rtmp

#==============================================================================

def PlayOrDownloadEpisode( episodeId, title, defaultFilename, swfPlayer ):
	xbmc.log('PlayOrDownloadEpisode swfPlayer: ' + swfPlayer)

	rtmp = InitializeRTMP(episodeId, swfPlayer)

	action = GetAction()	

	if ( action == 1 ):
		# Play
		Play(rtmp, title)
		##
		SetSubtitles(episodeId)
		##
	else:
		# Download
		Download(rtmp, defaultFilename)

	return

#==============================================================================

def GetUrlLibProxies():
	proxy = GetProxy()
	
	if proxy is None  or proxy == '':
		return None

	return {'http' : 'http://%s' % proxy}

def DoSearch():
	# Search
	kb = xbmc.Keyboard( "", __language__(30500) )
	kb.doModal()
	if ( kb.isConfirmed() == False ): return
	query = kb.getText()
	DoSearchQuery( query )

def DoSearchQuery( query ):
	data = geturllib.GetURL( "http://www.channel4.com/search/predictive/?q=%s" % mycgi.URLEscape(query), 10000, GetUrlLibProxies() )
	infos = re.findall( '{"imgUrl":"(.*?)".*?"value": "(.*?)".*?"siteUrl":"(.*?)","fourOnDemand":"true"}', data, re.DOTALL )
	listItems = []
	for info in infos:
		image = info[0]
		title = info[1]
		progUrl  = info[2]
		
		title = title.replace( '&amp;', '&' )
		title = title.replace( '&pound;', '£' )
		title = title.replace( '&quot;', "'" )
		
		image = "http://www.channel4.com" + image
		showId = re.search( 'programmes/(.*?)/4od', progUrl, re.DOTALL ).groups()[0]
		newListItem = xbmcgui.ListItem( title )
		newListItem.setThumbnailImage(image)
		url = __BaseURL__ + '?show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(title)
		listItems.append( (url,newListItem,True) )
	xbmcplugin.addDirectoryItems( handle=__PluginHandle__, items=listItems )
	xbmcplugin.setContent(handle=__PluginHandle__, content='tvshows')
	xbmcplugin.endOfDirectory( handle=__PluginHandle__, succeeded=True )
                                      

#==============================================================================

def remove_leading_slash(data):
    p = re.compile(r'/')
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
   
if __name__ == "__main__":

	try:
		geturllib.SetCacheDir( CACHE_FOLDER )
		if ( mycgi.EmptyQS() ):
			ShowCategories()
		else:
			(category, showId, episodeId, title, search, swfPlayer, order, page) = mycgi.Params( 'category', 'show', 'ep', 'title', 'search', 'swfPlayer', 'order', 'page' )
			if ( search <> '' ):
				DoSearch()
			elif ( showId <> '' ):
				ShowEpisodes( showId, title )
			elif ( category <> '' ):
				ShowCategory( category, title, order, page )
			elif ( episodeId <> '' ):
				PlayOrDownloadEpisode( episodeId, title, mycgi.Param('fn'), swfPlayer )
	except:
		# Make sure the text from any script errors are logged
		import traceback
		traceback.print_exc(file=sys.stdout)
		raise

# -*- coding: utf-8 -*-

import xbmc
from xbmc import log
from xbmcaddon import Addon

from rte import RTEProvider

# Provider names

__providers__ = [RTEProvider()]


def getProvider(name):
	log("ProviderFactory(" + str(name) + ")", xbmc.LOGDEBUG)

	for provider in __providers__:
		if name == provider.GetProviderId():
			return provider

	# TODO Log error

def getProviderList():
	return __providers__

# -*- coding: utf-8 -*-

import xbmc
from xbmc import log
from xbmcaddon import Addon

from rte import RTEProvider
from tv3 import TV3Provider

# Provider names

__providers__ = [RTEProvider(), TV3Provider()]


def getProvider(name):
    log("ProviderFactory(" + str(name) + ")", xbmc.LOGDEBUG)

    for provider in __providers__:
        if name == provider.GetProviderId():
            return provider

    # Provider '%s' not found
    logException = LoggingException(u"getProvider()", self.language(40140) % name, html)

    # Error getting provider, Provider '%s' not found
    logException.process(self.language(40150), self.language(40140) % name, self.logLevel(xbmc.LOGERROR))

def getProviderList():
    return __providers__

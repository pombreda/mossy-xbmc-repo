## Details ##

If you're having trouble using the plugin from abroad it may be due to geo-blocking on some or all of the services. The current services are

  * RTE
  * AerTV
  * TV3
  * TG4

Usually AerTV and live TV on RTE are geo-blocked (TG4 is an unknown quantity at this point).

Geo-block related settings - Forwarded IP and proxy details can be configured in the plugin settings dialog under the "Proxy General" tab.

To apply the settings to a particular service, go to the "Proxy per Service" tab. There you'll be able to select from the following options for each service:

  * None
  * Forwarded IP
  * Proxy for HTTP
  * Proxy for HTTP and streams


**Forwarded IP** sends a header along with your HTTP requests that fools some webservers into thinking that your IP is something it's not (i.e. within Ireland). _Note:_ Using a DNS service like Overplay's SmartDNS may
interfere with your ability to work around the geo-blocking. It may be worth your while to turn off such services while you are trying these settings.


&lt;BR&gt;



&lt;BR&gt;


**Forwarded IP**

&lt;BR&gt;


Change the setting to **Forwarded IP** for the services for which you are having problems. There should be no need to make any other changes. This seems to work for some people, not for others. There is a context menu item **Test Forwarded IP** in the plugins main menu (listing **RTE**, **TV3**, etc). Select this menu item to check whether or not webservers are seeing the Forwarded IP header as intended.

**Proxy for HTTP**

&lt;BR&gt;


If that doesn't work for you then you may need to use a proxy. To do so enter your proxy details in the **Proxy General** section, and set the relevant service to **Proxy for HTTP** in the **Proxy per Service** section. That will make all HTTP requests through the proxy, but the video streams will still be passed directly.

**Proxy for HTTP and streams**

&lt;BR&gt;


If that doesn't work change the setting to **Proxy for HTTP and streams**. That will only work for proxies that do not require a username and password and requires a fairly fast connection between your proxy and the service and also between the proxy and yourself in order for the video to play correctly.

This method requires a recent version of librtmp, click [here](librtmp.md) for more info.

If you have a suitable version of librtmp installed then you should see the following line in the XBMC log when you attempt to play a video using the **Proxy for HTTP and streams** method:

`Connecting via SOCKS proxy: `


&lt;BR&gt;



&lt;BR&gt;



&lt;BR&gt;


This method will use your proxy settings for everything, web and streams, but will **not** use the proxy username or password for streams and will **only** work with SOCKS proxies.



### Alternatives ###

If you have no luck with the Forwarded IP or proxy settings, then you may need to use some kind of third party service like VPN or a DNS forwarder.
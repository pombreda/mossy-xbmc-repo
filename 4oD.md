### What is a proxy? ###
First you need to find a UK based proxy (Google is your friend). A proxy is a server through which you can pass your web traffic, the website that you connect to through the proxy then thinks that your traffic is coming from the proxy, so if the proxy is in the UK then you appear to be in the UK.

You probably need to pay for a proxy, the free ones aren't likely to be reliable enough.

### Configuration ###

Proxy details can be configured in the plugin settings dialog under the "Proxy" tab. There you'll be able to select from the following options for "Method":

  * None
  * Proxy for HTTP
  * Proxy for HTTP and streams


&lt;BR&gt;


**Proxy for HTTP**

&lt;BR&gt;


This setting is intended for users who are blocked on web pages, but not on the video streams. You **must** set both a host and port. You **may** also set a username and password, if these are required by your proxy.

**Proxy for HTTP and streams**

&lt;BR&gt;


Each video can be streamed from either a Limelight server or an Akamai server. The server is determined randomly each time, with most videos seemingly coming from Akamai. Akamai streams seem to be geo-blocked, presumably this is true for all users. If this is the case for you then you can try the "Proxy for HTTP and streams" method.

This method requires a recent version of librtmp, click [here](librtmp.md) for more info.

If you have a suitable version of librtmp installed then you should see the following line in the XBMC log when you attempt to play a video using the **Proxy for HTTP and streams** method:

`Connecting via SOCKS proxy: `


&lt;BR&gt;



&lt;BR&gt;



&lt;BR&gt;


This method will use your proxy settings for everything, web and streams, but will **not** use the proxy username or password for streams and will **only** work with SOCKS proxies.



&lt;BR&gt;

If you have no luck with the proxy settings, then you may need to use some kind of third party service like VPN or a DNS forwarder.
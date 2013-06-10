TITLE = 'A&E'
VIDEOS_URL = 'http://www.aetv.com/videos/'
BASE_PATH = 'http://www.aetv.com'

####################################################################################################
def Start():

	# setup the default viewgroups for the plugin	
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

	# Setup the default attributes for the ObjectContainer
	ObjectContainer.title1 = TITLE
	ObjectContainer.view_group = 'InfoList'

	# Setup some basic things the plugin needs to know about
	HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler('/video/aetv', TITLE)
def MainMenu():

	oc = ObjectContainer(view_group='List')

	data = HTML.ElementFromURL(VIDEOS_URL)

	# to get all shows from main video page xpath: //ul[@id='av-list1']/li/a
	showList = data.xpath("//ul[@id='av-list1']/li/a")

	# if it's desirable to get only full episode shows at some point use this instead:
	#showList = data.xpath("id('Video')/li/a[contains(text(), 'Full Episode')]")

	# 58 results from the main /videos/ page (as above)
	# or we can also pull from the All Vidoes page - http://www.aetv.com/allshows.jsp
	# xpath: //ul[@id='NowShowing_container_unordered']/li/a
	# 37 results from this page -- not sure if this is up and coming or legacy, let's keep this
	# info around just in case

	for s in showList:
		if s.get('href')[:7]=="http://":
			url = s.get('href')
		else:
			url= BASE_PATH + s.get('href')

		# we can't currently handle "classics", "lifestyle" or "indiefilms"
		if url.startswith("http://www.aetv.com/classic/video/") or url.startswith("http://www.aetv.com/lifestyle/video/") or url.startswith("http://www.aetv.com/indiefilms/"):
			continue

		show=s.xpath('text()')[0]

		oc.add(
			DirectoryObject(
				key = Callback(ShowsPage, url=url, title=show),
				title = show
			)
		)

	return oc

####################################################################################################
@route('/video/aetv/showspage')
def ShowsPage(url, title):

	oc = ObjectContainer(title2=title, view_group='InfoList')
	data = HTML.ElementFromURL(url)		
	allData = data.xpath("//div[contains(@class,'video_playlist-item') and not(contains(@class, 'locked'))]")

	for s in allData:
		try:
			iid = s.xpath("./*[contains(@class,'id_holder')]/text()")[0]
			title = s.xpath(".//p[@class='video_details-title']/text()")[0]
			if s.xpath("./p[1]/strong[contains(text(),'CLIP')]"):
				title = "CLIP: "+title

			thumb_url = s.xpath("./a/img/@realsrc")[0]
			Log.Debug("thumb_url: "+thumb_url)
			video_url = s.xpath("./a/@onclick")[0].split("'")[1] + "#" + iid
			duration = Datetime.MillisecondsFromString(s.xpath("./p/span/text()")[0])
			try: episode = int(s.xpath("./div[contains(@class,'video_details')]/p[contains(text(), 'Episode')]/text()")[0].split(':')[1])
			except: episode=0

			summary = s.xpath("./div[contains(@class,'video_details')]/p[contains(@class,'video_details-synopsis')]/text()")[0]

			oc.add(
				EpisodeObject(
					url = video_url,
					title = title,
					duration = duration,
					summary = summary, 
	 				thumb = Resource.ContentsOfURLWithFallback(url=thumb_url),
					index = episode
				)
			)
		except:
			# if we land here we didn't have appropriate data (mostly like iid) to playback so skip this one
			continue

	return oc

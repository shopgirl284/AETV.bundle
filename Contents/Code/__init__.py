TITLE = 'A&E'
SHOWS_URL = 'http://www.aetv.com/shows'
BASE_PATH = 'http://www.aetv.com'
INNER_CONTAINER = '?_pjax=.inner-container'

####################################################################################################
def Start():

	ObjectContainer.title1 = TITLE
	HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler('/video/aetv', TITLE)
def MainMenu():

	oc = ObjectContainer()

	oc.add(DirectoryObject(key=Callback(AllShow), title="Shows"))
	oc.add(DirectoryObject(key=Callback(AllSection, title="Videos"), title="Videos"))

	return oc

####################################################################################################
@route('/video/aetv/allshow')
def AllShow():

	oc = ObjectContainer()

	oc.add(DirectoryObject(key=Callback(PopShows, title="Most Popular"), title="Most Popular"))
	oc.add(DirectoryObject(key=Callback(MainShows, title="Featured"), title="Featured"))
	oc.add(DirectoryObject(key=Callback(MainShows, title="Classics"), title="Classics"))

	return oc

#####################################################################################################
@route('/video/aetv/mainshows')
def MainShows(title):

	oc = ObjectContainer(title2=title)

	data = HTML.ElementFromURL(SHOWS_URL)
	# this gets shows from each section of the menu on the show page for featured and classics
	showList = data.xpath('//div/strong[text()="%s	"]/parent::div/following-sibling::div//ul/li/a' %title)

	for s in showList:
		url = s.xpath('./@href')[0]

		if not url.startswith('http://'):
			url = BASE_PATH + url

		show = s.xpath('text()')[0]

		oc.add(DirectoryObject(key = Callback(ShowSection, url=url, title=show), title = show))

	return oc

###################################################################################################
# This function gets the shows that have images for popular shows
@route('/video/aetv/popshows')
def PopShows(title):

	oc = ObjectContainer(title2=title)

	data = HTML.ElementFromURL(SHOWS_URL)
	showList = data.xpath('//div/h2[text()="Most Popular"]/parent::div//li/div/a')

	for s in showList:
		thumb = s.xpath('./img/@src')[0]
		url = s.xpath('./@href')[0]

		if not url.startswith('http://'):
			url= BASE_PATH + url

		show = s.xpath('./img/@alt')[0]

		oc.add(DirectoryObject(key = Callback(ShowSection, url=url, title=show, thumb = thumb), thumb = thumb, title = show))

	return oc

####################################################################################################
# This function sets up the url and xpath for the All video page and splits them into full episodes and clips
# Since the main videos page only offers one url for all videos, the xpath(vid_type) is used to break them up 
# into full episodes or clips
@route('/video/aetv/allsection')
def AllSection(title):

	oc = ObjectContainer(title2=title)
	url='http://www.aetv.com/video'

	oc.add(DirectoryObject(key=Callback(ShowsPage, title="Full Episodes", url=url, vid_type='full-episode'), title="Full Episodes"))
	oc.add(DirectoryObject(key=Callback(ShowsPage, title="Clips", url=url, vid_type='clips'), title="Clips"))

	return oc

####################################################################################################
# This function sets up the url and xpath for shows and splits them into full episodes and clips
# Since the xpath(vid_type) used for show videos is always 'all-videos', we break them up by adding 
# full episodes or clips to the end of the url
@route('/video/aetv/showsection')
def ShowSection(title, url, thumb=''):

	oc = ObjectContainer(title2=title)
	vid_type = 'all-videos'
	url = url +'/video/'

	if thumb:
		oc.add(DirectoryObject(key=Callback(ShowsPage, title="Full Episodes", url=url + 'full-episodes', vid_type=vid_type), title="Full Episodes", thumb=thumb))
		oc.add(DirectoryObject(key=Callback(ShowsPage, title="Clips", url=url + 'clips', vid_type=vid_type), title="Clips", thumb=thumb))
	else:
		oc.add(DirectoryObject(key=Callback(ShowsPage, title="Full Episodes", url=url + 'full-episodes', vid_type=vid_type), title="Full Episodes"))
		oc.add(DirectoryObject(key=Callback(ShowsPage, title="Clips", url=url + 'clips', vid_type=vid_type), title="Clips"))

	return oc

####################################################################################################
@route('/video/aetv/showspage')
def ShowsPage(url, title, vid_type):

	oc = ObjectContainer(title2=title)
	section_title = title

	if url.endswith(INNER_CONTAINER):
		local_url = url
	else:
		local_url = url + INNER_CONTAINER

	data = HTML.ElementFromURL(local_url)		
	# The class for videos from shows no longer contains a behind wall
	# So changed this xpath to look for data-behind-the-wall field since both types have that
	allData = data.xpath('//ul[@id="%s-ul"]/li[not(contains(@data-behind-the-wall, "true"))]' %vid_type)

	for s in allData:
		class_info = s.xpath('./@class')[0]

		# Ads are picked up in this list so we check for an ending of -ad
		if class_info.endswith('-ad'):
			continue

		title = s.xpath('./@data-title')[0]
		thumb_url = s.xpath('./a/img/@src')[0]

		video_url = s.xpath('./a/@href')[0]
		if not video_url.startswith('http:'):
			video_url = BASE_PATH + video_url

		duration = Datetime.MillisecondsFromString(s.xpath('.//span[contains(@class,"duration")]/text()')[0])
		summary = s.xpath("./@data-description")[0]

		try: show_name = s.xpath('.//h5[@class="series"]/text()')[0]
		except: show_name = None
		if show_name:
			title = '%s - %s' %(show_name, title)
        
		try: episode = int(s.xpath('.//span[contains(@class,"tile-episode")]/text()')[0].split('E')[1])
		except: episode = None
            
		if episode:
			try: season = int(s.xpath('.//span[contains(@class,"season")]/text()')[0].split('S')[1])
			except: season = 1
			date = Datetime.ParseDate(s.xpath('./@data-date')[0].split(':')[1])

			oc.add(
				EpisodeObject(
					url = video_url,
					title = title,
					duration = duration,
					summary = summary,
					thumb = Resource.ContentsOfURLWithFallback(url=thumb_url),
					originally_available_at = date,
					index = episode,
					season = season
				)
			)
			oc.objects.sort(key = lambda obj: obj.originally_available_at, reverse=True)
		else:
			oc.add(
				VideoClipObject(
					url = video_url,
					title = title,
					duration = duration,
					summary = summary,
					thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
				)
			)
	# Need to check for a next page url but only for individual shows
	if vid_type=='all-videos':
		try: next_page = data.xpath('//ul/li[contains(@class, "pager-next")]/a/@href')[0]
		except: next_page = None
		if next_page:
			oc.add(NextPageObject(key=Callback(ShowsPage, title=section_title, url=BASE_PATH + next_page, vid_type=vid_type), title = L("Next Page ...")))
			
	if len(oc) < 1:
		#Log ('still no value for objects')
		return ObjectContainer(header="Empty", message="There are no videos to display for this show right now.") 
	else:
		return oc

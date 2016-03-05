TITLE = 'A&E'
SHOWS_URL = 'http://www.aetv.com/shows'
VIDEO_URL = 'http://www.aetv.com/video'
BASE_PATH = 'http://www.aetv.com'
INNER_CONTAINER = '_pjax=.inner-container'

####################################################################################################
def Start():

    ObjectContainer.title1 = TITLE
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler('/video/aetv', TITLE)
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(AllShow), title="Shows"))
    oc.add(DirectoryObject(key=Callback(ShowsPageOld, title="Full Episodes", url=VIDEO_URL, vid_type='full-episode'), title="Full Episodes"))

    return oc

####################################################################################################
@route('/video/aetv/allshow')
def AllShow():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(MainShows, title="Most Popular"), title="Most Popular"))
    oc.add(DirectoryObject(key=Callback(MainShows, title="Current Shows"), title="Current Shows"))
    #oc.add(DirectoryObject(key=Callback(MainShows, title="Shows"), title="Current"))
    oc.add(DirectoryObject(key=Callback(MainShows, title="Classics"), title="Classics"))

    return oc

#####################################################################################################
# This function creates a list of shows for each section on the show page
@route('/video/aetv/mainshows')
def MainShows(title):

    oc = ObjectContainer(title2=title)
    data = HTML.ElementFromURL(SHOWS_URL)
    if 'Popular' not in title:
        try: title = title.split()[1]
        except: title = title
        title = title + '-list'
    showList = data.xpath('//div[@id="%s"]//ul/li' %title.lower().replace(' ', '-'))

    for s in showList:
        if s.xpath('./@class')[0] == 'ad':
            continue
        url = s.xpath('.//@href')[0]
        try: show = s.xpath('./a/text()')[0]
        except: show = s.xpath('.//h4/text()')[0]
        try: thumb = s.xpath('.//img/@src')[0]
        except: thumb = None
        try: summary = ''.join(s.xpath('.//div[@class="scrollpane"]//text()')).strip()
        except: summary = ''
        oc.add(DirectoryObject(
            key = Callback(ShowSeason, url = url, title = show, thumb = thumb),
            title = show,
            summary = summary,
            thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc

####################################################################################################
# This function pulls the season options for a show
@route('/video/aetv/showseason')
def ShowSeason(title, url, thumb=''):

    oc = ObjectContainer(title2=title)
    data = HTML.ElementFromURL(url)
    # If there isn't a thumb, then we pull the background image used in the new format 
    if not thumb:
        try: thumb = data.xpath('//div[@class="hero-img-container"]/@style')[0].split('image:url(')[1].split('?')[1]
        # If the thumb xpath does not work, it is not the new format, so we send it to the old player function 
        except:
            oc.add(DirectoryObject(
                key=Callback(ShowsPageOld, title="All Videos", url=url +'/video/', vid_type='all-videos', show=title),
                title="All Videos"
            ))
            
    for item in data.xpath('//ul[@id="season-dropdown"]/li'):
        seas_url = BASE_PATH + item.xpath('./@data-href')[0]
        seas_title = item.xpath('./text()')[0]
        season = int(seas_title.split()[1])
        oc.add(DirectoryObject(
            key=Callback(ShowsPage, title=seas_title, url=seas_url, season=season),
            title=seas_title,
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))

    if len(oc) < 1:
        oc.add(DirectoryObject(
            key=Callback(ShowsPage, title="Current Season", url=url, season=1),
            title="Current Season",
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))
    return oc

####################################################################################################
# This function produces videos for the new format for shows
@route('/video/aetv/showspage', season=int)
def ShowsPage(url, title, season=0):

    oc = ObjectContainer(title2=title)
    section_title = title

    data = HTML.ElementFromURL(url)		
    show_name = data.xpath('//meta[@name="aetn:SeriesTitle"]/@content')[0]
    # Check for locked shows
    # VIDEO THAT HAVE AN EPISODE TYPE OF FREE ARE ACTUALLY THE LOCKED VIDEOS AND INFO ONES HAVE NO VIDEO
    allData = data.xpath('//div[contains(@class, "episode-item") and not(contains(@data-episodetype, "free"))  and not(contains(@data-episodetype, "info"))]')

    for s in allData:
        video_url = s.xpath('./@data-canonical')[0]
        if not video_url.startswith('http:'):
            video_url = BASE_PATH + video_url
            title = s.xpath('.//strong[@class="episode-name"]/text()')[0]
            thumb_url = s.xpath('.//img/@data-original')[0]
            # There are a few full episodes that have no duration or content rating
            # New shows with only preview clips just have the url, thumb and title fields
            try: duration = Datetime.MillisecondsFromString(s.xpath('.//dd[@aetn-key="duration"]/text()')[0].replace('m ', ':').replace('s', ''))
            except: duration = 0
            try: content_rating = s.xpath('.//dd[@aetn-key="ratings"]/text()')[0]
            except: content_rating = ''
            try: date = Datetime.ParseDate(s.xpath('.//p[@class="episode-airdate"]/text()')[0].split('on ')[1])
            except: date = None
            if "Current" in section_title:
                try: season = int(s.xpath('.//strong[@class="season-number"]/text()')[0].split()[1])
                except: pass
            try: episode = int(s.xpath('.//strong[@class="episode-number"]/text()')[0].split()[1])
            except: episode = 0
            try: summary = s.xpath('.//p[@class="description"]/text()')[0]
            except: summary = ''

            oc.add(
                EpisodeObject(
                    url = video_url,
                    title = title,
                    duration = duration,
                    summary = summary,
                    thumb = Resource.ContentsOfURLWithFallback(url=thumb_url),
                    originally_available_at = date,
                    content_rating = content_rating,
                    index = episode,
                    season = season)
            )
			
    if len(oc) < 1:
        #Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos to display for this show right now.") 
    else:
        return oc
####################################################################################################
# This function pulls the videos from the old format pages. It is used for the Full Episode section, 
# and the A&E Indie Films show.
@route('/video/aetv/showspageold')
def ShowsPageOld(url, title, vid_type, show=''):

    oc = ObjectContainer(title2=title)
    section_title = title

    if url.endswith(INNER_CONTAINER):
        local_url = url
    else:
        local_url = '%s?%s' %(url, INNER_CONTAINER)

    data = HTML.ElementFromURL(local_url)		
    # Check for locked videos
    allData = data.xpath('//ul[@id="%s-ul"]/li[not(contains(@class, "behind-wall"))]' %vid_type)

    for s in allData:
        # Ads are list items too, so we skip those
        if "aetv-isotope-ad" in s.xpath('./@class')[0]:
            continue

        video_url = s.xpath('./a/@href')[0]
        if not video_url.startswith('http:'):
            video_url = BASE_PATH + video_url
        title = s.xpath('./@data-title')[0]
        try: thumb_url = s.xpath('.//img/@data-src')[0]
        except: thumb_url = s.xpath('.//img/@src')[0]
        duration = Datetime.MillisecondsFromString(s.xpath('.//span[contains(@class,"duration")]/text()')[0])
        try: date = Datetime.ParseDate(s.xpath('./@data-date')[0].split(':')[1])
        except: date = None
        summary = s.xpath("./@data-description")[0]
        try: season = int(s.xpath('./@data-season')[0])
        except: season = 1
        if show:
            show_name = show
        else:
            show_name = s.xpath('.//h5[@class="series"]/text()')[0]
        #Log('the value of show_name is %s' %show_name)
        #vid_type = s.xpath('./@data-video-type')[0]
            
        oc.add(
            EpisodeObject(
                show = show_name,
                season = season,
                url = video_url,
                title = title,
                duration = duration,
                summary = summary,
                originally_available_at = date,
                thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
            )
        )
    oc.objects.sort(key = lambda obj: obj.originally_available_at, reverse=True)
    # Need to check for a next page url but only for individual shows
    # THIS CODE SHOULD NOT BE NEEDED ANYMORE SINCE ONLY ONE SHOW STILL USES THIS OLD FORMAT AND IT HAS NO PAGING
    if local_url.startswith('http://www.aetv.com/shows/'):
        try: next_page = data.xpath('//div[@id="%-column"]//li[@class="pager-next"]/a/@href' %vid_type)[0].split('&')[0]
        except: next_page = None
        if next_page:
            next_page = '%s%s&%s' %(BASE_PATH, next_page, INNER_CONTAINER)
            oc.add(NextPageObject(key=Callback(ShowsPage, title=section_title, url=next_page, vid_type=vid_type), title = L("Next Page ...")))
			
    if len(oc) < 1:
        #Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos to display right now.") 
    else:
        return oc

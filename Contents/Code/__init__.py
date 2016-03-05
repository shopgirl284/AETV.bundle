TITLE = 'A&E'
PREFIX = '/video/aetv'

BASE_PATH = 'http://www.aetv.com'
VIDEO_URL = 'http://www.aetv.com/video'
INNER_CONTAINER = '_pjax=.inner-container'

SHOWS = 'http://wombatapi.aetv.com/shows2/ae'
SIGNATURE_URL = 'http://servicesaetn-a.akamaihd.net/jservice/video/components/get-signed-signature?url=%s'
SMIL_NS = {"a":"http://www.w3.org/2005/SMIL21/Language"}

####################################################################################################
def Start():

    ObjectContainer.title1 = TITLE
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler(PREFIX, TITLE)
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(Shows, title="Shows"), title="Shows"))
    oc.add(DirectoryObject(key=Callback(ShowsPageOld, title="Full Episodes", url=VIDEO_URL, vid_type='full-episode'), title="Full Episodes"))

    return oc

####################################################################################################
@route(PREFIX + '/shows')
def Shows(title, showPosition=''):
    oc = ObjectContainer(title2=title)
    
    json_data = JSON.ObjectFromURL(SHOWS)
    
    for item in json_data:
        if showPosition and item['showPosition']=='Position Not Set':
            continue
            
        if not (item['hasNoVideo'] == 'false' or item['hasNoHDVideo'] == 'false'):
            continue
        
        oc.add(
            TVShowObject(
                key = Callback(
                    Seasons,
                    show_id = item['showID'],
                    show_title = item['detailTitle'],
                    episode_url = item['episodeFeedURL'],
                    clip_url = item['clipFeedURL'],
                    show_thumb = item['detailImageURL2x']
                ),
                rating_key = item['showID'],
                title = item['detailTitle'],
                summary = item['detailDescription'],
                thumb = item['detailImageURL2x'],
                studio = item['network']
            )
        )

    oc.objects.sort(key = lambda obj: obj.title)
    
    return oc

####################################################################################################
@route(PREFIX + '/seasons')
def Seasons(show_id, show_title, episode_url, clip_url, show_thumb):

    oc = ObjectContainer(title2=show_title)
    
    json_data = JSON.ObjectFromURL(episode_url + '&filter_by=isBehindWall&filter_value=false')
    
    seasons = {}
    for item in json_data['Items']:
        if 'season' in item:
            if not int(item['season']) in seasons:
                seasons[int(item['season'])] = 1
            else:
                seasons[int(item['season'])] = seasons[int(item['season'])] + 1
    
    for season in seasons:
        oc.add(
            SeasonObject(
                key = Callback(
                    Episodes,
                    show_title = show_title,
                    episode_url = episode_url,
                    clip_url = clip_url,
                    show_thumb = show_thumb,
                    season = season
                ),
                title = 'Season %s' % season,
                rating_key = show_id + str(season),
                index = int(season),
                episode_count = seasons[season],
                thumb = show_thumb
            )
        )
 
    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='This show does not have any unlocked videos available.')
    else:
        oc.objects.sort(key = lambda obj: obj.index, reverse = True)
        return oc 
    

####################################################################################################
@route(PREFIX + '/episodes')
def Episodes(show_title, episode_url, clip_url, show_thumb, season):

    oc = ObjectContainer(title2=show_title)
    json_data = JSON.ObjectFromURL(episode_url + '&filter_by=isBehindWall&filter_value=false')
    
    for item in json_data['Items']:
        if 'season' in item:
            if not int(item['season']) == int(season):
                continue
        
        url = item['siteUrl']
        title = item['title']
        summary = item['description'] if 'description' in item else None
        
        if 'thumbnailImage2xURL' in item:
            thumb = item['thumbnailImage2xURL']
        elif 'stillImageURL' in item:
            thumb = item['stillImageURL']
        elif 'modalImageURL' in item:
            thumb = item['modalImageURL']
        else:
            thumb = show_thumb
            
        show = item['seriesName'] if 'seriesName' in item else show_title
        duration = int(item['totalVideoDuration']) if 'totalVideoDuration' in item else None
        originally_available_at = Datetime.ParseDate(item['originalAirDate'].split('T')[0]).date() if 'originalAirDate' in item else None
        index = int(item['episode']) if 'episode' in item else None
        season = int(item['season']) if 'season' in item else None
        
        oc.add(
            EpisodeObject(
                url = url,
                title = title,
                summary = summary,
                thumb = thumb,
                art = show_thumb,
                show = show,
                duration = duration,
                originally_available_at = originally_available_at,
                index = index,
                season = season
            )
        )
    
    oc.objects.sort(key = lambda obj: obj.index)
    
    return oc
####################################################################################################
# This function pulls the videos from the old format pages. It is used for the Full Episode section 
@route(PREFIX +'/showspageold')
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
			
    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos to display right now.") 
    else:
        return oc

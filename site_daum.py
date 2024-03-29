
# -*- coding: utf-8 -*-
import requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html

from framework import SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite


from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTvDaum, EntityShow, EntityEpisode
from .site_util import SiteUtil

logger = P.logger


class SiteDaum(object):
    site_name = 'daum'
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    @classmethod
    def get_show_info_on_home(cls, root):
        try:
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/a')
            # 2019-05-13
            #일밤- 미스터리 음악쇼 복면가왕 A 태그 2개
            if len(tags) < 1:
                return
            tag_index = len(tags)-1
            #entity = {}
            entity = EntitySearchItemTvDaum(cls.site_name)

            entity.title = tags[tag_index].text
            match = re.compile(r'q\=(?P<title>.*?)&').search(tags[tag_index].attrib['href'])
            if match:
                entity.title = py_urllib.unquote(match.group('title'))
            entity.code = cls.module_char + cls.site_char + re.compile(r'irk\=(?P<id>\d+)').search(tags[tag_index].attrib['href']).group('id')

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/span')
            if len(tags) == 1:
                if tags[0].text == u'방송종료' or tags[0].text == u'완결':
                    entity.status = 2
                elif tags[0].text == u'방송예정':
                    entity.status = 0

            #entity.image_url = 'https:' + root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src']
            # 악동탐정스 시즌2
            try:
                entity.image_url = cls.process_image_url(root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src'])
            except:
                entity.image_url = None

            #logger.debug('get_show_info_on_home status: %s', entity.status)
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div')
            entity.extra_info = SiteUtil.change_html(tags[0].text_content().strip())

            #logger.debug('get_show_info_on_home extra_info: %s', entity.extra_info)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/a')
            if len(tags) == 1:
                entity.studio = tags[0].text
            else:
                tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span[1]')
                if len(tags) == 1:
                    entity.studio = tags[0].text
            #logger.debug('get_show_info_on_home studio: %s', entity.studio)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span')
            extra_infos = [tag.text_content() for tag in tags]
            logger.debug(extra_infos)
            #tmps = extra_infos[1].strip().split(' ')
            # 2021-11-03 
            # 홍루몽.  중국 방송사는 a 태그가 없기 떄문에 방송사가 장르가 되어버린다.
            entity.genre = extra_infos[0]
            if extra_infos[1] in ['미국드라마', '중국드라마', '영국드라마', '일본드라마', '대만드라마', '기타국가드라마']:
                entity.genre = extra_infos[1]
                entity.studio = extra_infos[0]
            if entity.genre in ['미국드라마', '중국드라마', '영국드라마', '일본드라마', '대만드라마', '기타국가드라마']:
                entity.status = 1
            #logger.debug(tmps)
            #if len(tmps) == 2:
            try: entity.episode = int(re.compile(r'(?P<epi>\d{1,4})%s' % u'부').search(entity.extra_info).group('epi'))
            except: entity.episode = -1
            entity.broadcast_info = extra_infos[-2].strip().replace('&nbsp;', ' ').replace('&nbsp', ' ')
            entity.broadcast_term = extra_infos[-1].split(',')[-1].strip()

            try: entity.year = re.compile(r'(?P<year>\d{4})').search(extra_infos[-1]).group('year')
            except: entity.year = 0

            entity.desc = root.xpath('//*[@id="tv_program"]/div[1]/dl[1]/dd/text()')[0]

            #logger.debug('get_show_info_on_home 1: %s', entity['status'])
            #시리즈
            entity.series = []
            
            try:
                tmp = entity.broadcast_term.split('.')
                if len(tmp) == 2:
                    entity.series.append({'title':entity.title, 'code' : entity.code, 'year' : entity.year, 'status':entity.status, 'date':'%s.%s' % (tmp[0], tmp[1])})
                else:
                    entity.series.append({'title':entity.title, 'code' : entity.code, 'year' : entity.year, 'status':entity.status, 'date':'%s' % (entity.year)})
            except Exception as exception:
                logger.debug('Not More!')
                logger.debug(traceback.format_exc())

            tags = root.xpath('//*[@id="tv_series"]/div/ul/li')

            if tags:
                # 2019-03-05 시리즈 더보기 존재시
                try:
                    more = root.xpath('//*[@id="tv_series"]/div/div/a')
                    if more:
                        url = more[0].attrib['href']
                        if not url.startswith('http'):
                            url = 'https://search.daum.net/search%s' % url
                        #logger.debug('MORE URL : %s', url)
                        if more[0].xpath('span')[0].text == u'시리즈 더보기':
                            #more_root = HTML.ElementFromURL(url)
                            more_root = SiteUtil.get_tree(url, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
                            tags = more_root.xpath('//*[@id="series"]/ul/li')
                except Exception as exception:
                    logger.debug('Not More!')
                    logger.debug(traceback.format_exc())

                find_1900 = False
                for tag in tags:
                    dic = {}
                    dic['title'] = tag.xpath('a')[0].text
                    #logger.debug(dic['title'])
                    dic['code'] = cls.module_char + cls.site_char + re.compile(r'irk\=(?P<id>\d+)').search(tag.xpath('a')[0].attrib['href']).group('id')
                    if tag.xpath('span'):
                        # 년도 없을 수 있음
                        dic['date'] = tag.xpath('span')[0].text
                        if dic['date'] is None:
                            dic['date'] = '1900'
                            find_1900 = True
                        else:
                            dic['year'] = re.compile(r'(?P<year>\d{4})').search(dic['date']).group('year')
                    else:
                        dic['year'] = None
                    entity.series.append(dic)
                # 뒷 시즌이 code가 더 적은 경우 있음. csi 라스베가스
                # 2021-03-29 전지적 짝사랑 시점
                if find_1900 or entity.year == 0:
                    entity.series = sorted(entity.series, key=lambda k: int(k['code'][2:]))
                else:
                    # 2021-06-06 펜트하우스3. 2는 2021.2로 나오고 3은 2021로만 나와서 00이 붙어 3이 위로 가버림
                    # 같은 년도는 코드로...
                    """
                    for item in entity.series:
                        tmp = item['date'].split('.')
                        if len(tmp) == 2:
                            item['sort_value'] = int('%s%s' % (tmp[0],tmp[1].zfill(2)))
                        elif len(tmp) == 1:
                            item['sort_value'] = int('%s00' % tmp[0])
                    entity.series = sorted(entity.series, key=lambda k: k['sort_value'])
                    """
                    for item in entity.series:
                        tmp = item['date'].split('.')
                        if len(tmp) == 2:
                            item['sort_value'] = int(tmp[0])
                        elif len(tmp) == 1:
                            item['sort_value'] = int(tmp[0])
                    entity.series = sorted(entity.series, key=lambda k: (k['sort_value'], int(k['code'][2:])))

            #동명
            entity.equal_name = []
            tags = root.xpath(u'//div[@id="tv_program"]//dt[contains(text(),"동명 콘텐츠")]//following-sibling::dd')
            if tags:
                tags = tags[0].xpath('*')
                for tag in tags:
                    if tag.tag == 'a':
                        dic = {}
                        dic['title'] = tag.text
                        dic['code'] = cls.module_char + cls.site_char + re.compile(r'irk\=(?P<id>\d+)').search(tag.attrib['href']).group('id')
                    elif tag.tag == 'span':
                        match = re.compile(r'\((?P<studio>.*?),\s*(?P<year>\d{4})?\)').search(tag.text)
                        if match:
                            dic['studio'] = match.group('studio')
                            dic['year'] = match.group('year')
                        elif tag.text == u'(동명프로그램)':
                            entity.equal_name.append(dic)
                        elif tag.text == u'(동명회차)':
                            continue
            #logger.debug(entity)
            return entity.as_dict()
        except Exception as exception:
            logger.debug('Exception get_show_info_by_html : %s', exception)
            logger.debug(traceback.format_exc())

    @classmethod
    def process_image_url(cls, url):
        tmps = url.split('fname=')
        if len(tmps) == 2:
            return py_urllib.unquote(tmps[1])
        else:
            return 'https' + url

    @classmethod 
    def get_kakao_play_url(cls, url):
        try:
            #https://tv.kakao.com/katz/v2/ft/cliplink/385912700/readyNplay?player=monet_html5&profile=HIGH&service=kakao_tv&section=channel&fields=seekUrl,abrVideoLocationList&startPosition=0&tid=&dteType=PC&continuousPlay=false&contentType=&1610102225387
            content_id = url.split('/')[-1]
            url = 'https://tv.kakao.com/katz/v2/ft/cliplink/{}/readyNplay?player=monet_html5&profile=HIGH&service=kakao_tv&section=channel&fields=seekUrl,abrVideoLocationList&startPosition=0&tid=&dteType=PC&continuousPlay=false&contentType=&{}'.format(content_id, int(time.time()))
            data = requests.get(url).json()
            return data['videoLocation']['url']
        except Exception as exception:
            logger.debug('Exception : %s', exception)
            logger.debug(traceback.format_exc())

    @classmethod 
    def change_date(cls, text):
        try:
            match = re.compile(r'(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})').search(text)
            if match:
                return match.group('year') + '-' + match.group('month').zfill(2) + '-'+ match.group('day').zfill(2)
        except Exception as exception:
            logger.debug('Exception : %s', exception)
            logger.debug(traceback.format_exc())
        return text

    #https://tv.kakao.com/api/v1/ft/channels/3601234/videolinks?sort=PlayCount&fulllevels=clipLinkList%2CliveLinkList&fields=ccuCount%2CisShowCcuCount%2CthumbnailUrl%2C-user%2C-clipChapterThumbnailList%2C-tagList&size=20&page=2&_=1610122871452

    #https://tv.kakao.com/api/v1/ft/channels/3601234/videolinks?sort=CreateTime&fulllevels=clipLinkList%2CliveLinkList&fields=ccuCount%2CisShowCcuCount%2CthumbnailUrl%2C-user%2C-clipChapterThumbnailList%2C-tagList&size=20&page=1&_=1610122871453

    @classmethod
    def get_kakao_video(cls, kakao_id, sort='CreateTime', size=20):
        #sort : CreateTime PlayCount
        try:
            url = 'https://tv.kakao.com/api/v1/ft/channels/{kakao_id}/videolinks?sort={sort}&fulllevels=clipLinkList%2CliveLinkList&fields=ccuCount%2CisShowCcuCount%2CthumbnailUrl%2C-user%2C-clipChapterThumbnailList%2C-tagList&size=20&page=1&_={timestamp}'.format(kakao_id=kakao_id, sort=sort, timestamp=int(time.time()))
            data = requests.get(url).json()

            ret = []
            for item in data['clipLinkList']:
                ret.append(EntityExtra('Featurette', item['clip']['title'], 'kakao', item['id'], premiered=item['createTime'].split(' ')[0], thumb=item['clip']['thumbnailUrl']).as_dict())
            return ret
        except Exception as exception:
            logger.debug('Exception : %s', exception)
            logger.debug(traceback.format_exc())
        return ret   









class SiteDaumTv(SiteDaum):
    
    site_base_url = 'https://search.daum.net'
    module_char = 'K'
    site_char = 'D'

    
    @classmethod
    def get_search_name_from_original(cls, search_name):
        search_name = search_name.replace('일일연속극', '').strip()
        search_name = search_name.replace('특별기획드라마', '').strip()
        search_name = re.sub(r'\[.*?\]', '', search_name).strip()
        search_name = search_name.replace(".", ' ')
        # 2020-10-10
        channel_list = ['채널 A', '채널A']
        for tmp in channel_list:
            if search_name.startswith(tmp):
                search_name = search_name.replace(tmp, '').strip()
        search_name = re.sub(r'^.{2,3}드라마', '', search_name).strip()
        #2019-08-01
        search_name = re.sub(r'^.{1,3}특집', '', search_name).strip()
        return search_name

    @classmethod 
    def search(cls, keyword, daum_id=None, year=None, image_mode='0'):
        try:
            keyword = cls.get_search_name_from_original(keyword)
            ret = {}
            if daum_id is None:
                url = 'https://search.daum.net/search?q=%s' % (py_urllib.quote(str(keyword)))
            else:
                url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(str(keyword)), daum_id)

            root = SiteUtil.get_tree(url, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            data = cls.get_show_info_on_home(root)
            #logger.debug(data)
            # KD58568 : 비하인드 더 쇼
            if data is not None and data['code'] in ['KD58568']:
                data = None
            if data is None:
                ret['ret'] = 'empty'
            else:
                ret['ret'] = 'success'
                ret['data'] = data
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret



    @classmethod 
    def info(cls, code, title):
        try:
            if title  == '모델': title = '드라마 모델'
            ret = {}
            show = EntityShow(cls.site_name, code)
            # 종영와, 방송중이 표현 정보가 다르다. 종영은 studio가 없음
            url = 'https://search.daum.net/search?w=tv&q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(str(title)), code[2:])
            show.home = url
            root = SiteUtil.get_tree(url, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            home_url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(str(title)), code[2:])
            
            #logger.debug(home_url)
            home_root = SiteUtil.get_tree(home_url, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            home_data = cls.get_show_info_on_home(home_root)

            #logger.debug('home_datahome_datahome_datahome_datahome_datahome_datahome_datahome_datahome_data')
            #logger.debug(home_data)

            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/strong')
            if len(tags) == 1:
                show.title = tags[0].text_content().strip()
                show.originaltitle = show.title
                show.sorttitle = show.title #unicodedata.normalize('NFKD', show.originaltitle)
                #logger.debug(show.sorttitle)
            """
            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[3]/span')
            # 이 정보가 없다면 종영
            if tags:
                show.studio = tags[0].text_content().strip()
                summary = ''    
                for tag in tags:
                    entity.plot += tag.text.strip()
                    entity.plot += ' '
                match = re.compile(r'(\d{4}\.\d{1,2}\.\d{1,2})~').search(entity.plot)
                if match:
                    show.premiered = match.group(1)
            """
            show.studio = home_data['studio']
            show.plot = home_data['desc']
            match = re.compile(r'(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})').search(home_data['broadcast_term'])
            if match:
                show.premiered = match.group('year') + '-' + match.group('month').zfill(2) + '-'+ match.group('day').zfill(2)
                show.year = int(match.group('year'))
            try:
                if show.year == '' and home_data['year'] != 0:
                    show.year = home_data['year']
            except:
                pass
                
            
            show.status = home_data['status']
            show.genre = [home_data['genre']]
            show.episode = home_data['episode']

            tmp = root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')
            #logger.debug(tmp)

            try:
                show.thumb.append(EntityThumb(aspect='poster', value=cls.process_image_url(root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src']), site='daum', score=-10))
            except:
                pass


            if True: 
                tags = root.xpath('//ul[@class="col_size3 list_video"]/li')
                for idx, tag in enumerate(tags):
                    if idx > 9:
                        break
                    a_tags = tag.xpath('.//a')
                    if len(a_tags) == 2:
                        thumb = cls.process_image_url(a_tags[0].xpath('.//img')[0].attrib['src'])
                        video_url = a_tags[1].attrib['href'].split('/')[-1]
                        title = a_tags[1].text_content()
                        date = cls.change_date(tag.xpath('.//span')[0].text_content().strip())
                        content_type = 'Featurette'
                        if title.find(u'예고') != -1:
                            content_type = 'Trailer'
                        show.extras.append(EntityExtra(content_type, title, 'kakao', video_url, premiered=date, thumb=thumb))


            for i in range(1,3):
                items = root.xpath('//*[@id="tv_casting"]/div[%s]/ul//li' % i)
                #logger.debug('CASTING ITEM LEN : %s' % len(items))
                for item in items:
                    actor = EntityActor(None)
                    cast_img = item.xpath('div//img')
                    #cast_img = item.xpath('.//img')
                    if len(cast_img) == 1:
                        actor.thumb = cls.process_image_url(cast_img[0].attrib['src'])
                        #logger.debug(actor.thumb)
                    
                    span_tag = item.xpath('span')
                    for span in span_tag:
                        span_text = span.text_content().strip()
                        tmp = span.xpath('a')
                        if len(tmp) == 1:
                            role_name = tmp[0].text_content().strip()
                            tail = tmp[0].tail.strip()
                            if tail == u'역':
                                actor.type ='actor'
                                actor.role = role_name.strip()
                            else:
                                actor.name = role_name.strip()
                        else:
                            if span_text.endswith(u'역'): actor.role = span_text.replace(u'역', '')
                            elif actor.name == '': actor.name = span_text.strip()
                            else: actor.role = span_text.strip()
                    if actor.type == 'actor' or actor.role.find(u'출연') != -1:
                        show.actor.append(actor)
                    elif actor.role.find(u'감독') != -1 or actor.role.find(u'연출') != -1:
                        show.director.append(actor)
                    elif actor.role.find(u'제작') != -1 or actor.role.find(u'기획') != -1 or actor.role.find(u'책임프로듀서') != -1:
                        show.director.append(actor)
                    elif actor.role.find(u'극본') != -1 or actor.role.find(u'각본') != -1:
                        show.credits.append(actor)
                    elif actor.name != u'인물관계도':
                        show.actor.append(actor)

            # 에피소드
            items = root.xpath('//*[@id="clipDateList"]/li')
            #show.extra_info['episodes'] = {}
            for item in items:
                epi = {}
                a_tag = item.xpath('a') 
                if len(a_tag) != 1:
                    continue
                epi['url'] = 'https://search.daum.net/search%s' % a_tag[0].attrib['href']
                tmp = item.attrib['data-clip']
                epi['premiered'] = tmp[0:4] + '-' + tmp[4:6] + '-' + tmp[6:8]
                match = re.compile(r'(?P<no>\d+)%s' % u'회').search(a_tag[0].text_content().strip())
                if match:
                    epi['no'] = int(match.group('no'))
                    show.extra_info['episodes'][epi['no']] = {'daum': {'code' : cls.module_char + cls.site_char + epi['url'], 'premiered':epi['premiered']}}

            tags = root.xpath('//*[@id="tv_program"]//div[@class="clipList"]//div[@class="mg_expander"]/a')
            show.extra_info['kakao_id'] = None
            if tags:
                tmp = tags[0].attrib['href']
                show.extra_info['kakao_id'] = re.compile('/(?P<id>\d+)/').search(tmp).group('id')

            tags = root.xpath("//a[starts-with(@href, 'http://www.tving.com/vod/player')]")
            #tags = root.xpath('//a[@contains(@href, "tving.com")')
            if tags:
                show.extra_info['tving_episode_id'] = tags[0].attrib['href'].split('/')[-1]

            ret['ret'] = 'success'
            ret['data'] = show.as_dict()

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret


    @classmethod
    def episode_info(cls, episode_code, include_kakao=False, is_ktv=True, summary_duplicate_remove=False):
        try:
            ret = {}
            episode_code = episode_code[2:]
            root = SiteUtil.get_tree(episode_code, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            items = root.xpath('//div[@class="tit_episode"]')
            entity = EntityEpisode(cls.site_name, episode_code)

            if len(items) == 1:
                tmp = items[0].xpath('strong')
                if len(tmp) == 1:
                    episode_frequency = tmp[0].text_content().strip()
                    match = re.compile(r'(\d+)').search(episode_frequency)
                    if match:
                        entity.episode = int(match.group(1))

                tmp = items[0].xpath('span[@class="txt_date "]')
                date1 = ''
                if len(tmp) == 1:
                    date1 = tmp[0].text_content().strip()
                    entity.premiered = cls.change_date(date1.split('(')[0])
                    entity.title = date1
                tmp = items[0].xpath('span[@class="txt_date"]')
                if len(tmp) == 1:
                    date2 = tmp[0].text_content().strip()
                    entity.title = ('%s %s' % (date1, date2)).strip()
            items = root.xpath('//p[@class="episode_desc"]')
            has_strong_tag = False
            strong_title = ''
            if len(items) == 1:
                tmp = items[0].xpath('strong')
                if len(tmp) == 1:
                    has_strong_tag = True
                    strong_title = tmp[0].text_content().strip()
                    if strong_title != 'None': 
                        if is_ktv:
                            entity.title = '%s %s' % (entity.title, strong_title)
                        else:
                            entity.title = strong_title
                        
                else:
                    if is_ktv == False:
                        entity.title = ''
            entity.title = entity.title.strip()
            summary2 = '\r\n'.join(txt.strip() for txt in root.xpath('//p[@class="episode_desc"]/text()'))
            if summary_duplicate_remove == False:
                entity.plot = '%s\r\n%s' % (entity.title, summary2)
            else:
                entity.plot = summary2.replace(strong_title, '').strip()
            
            items = root.xpath('//*[@id="tv_episode"]/div[2]/div[1]/div/a/img')
            if len(items) == 1:
                entity.thumb.append(EntityThumb(aspect='landscape', value=cls.process_image_url(items[0].attrib['src']), site=cls.site_name, score=-10))

            if include_kakao:
                tags = root.xpath('//*[@id="tv_episode"]/div[3]/div/ul/li')
                for idx, tag in enumerate(tags):
                    if idx > 9:
                        break
                    a_tags = tag.xpath('.//a')
                    if len(a_tags) == 2:
                        thumb = cls.process_image_url(a_tags[0].xpath('.//img')[0].attrib['src'])
                        #video_url = cls.get_kakao_play_url(a_tags[1].attrib['href'])
                        video_url = a_tags[1].attrib['href'].split('/')[-1]
                        title = a_tags[1].text_content()
                        #logger.debug(video_url)
                        date = cls.change_date(tag.xpath('.//span')[0].text_content().strip())
                        entity.extras.append(EntityExtra('Featurette', title, 'kakao', video_url, premiered=date, thumb=thumb))
            

            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret



    @classmethod
    def get_actor_eng_name(cls, name):
        try:
            ret = {}
            url = 'https://search.daum.net/search?w=tot&q=%s' % (name)
            root = SiteUtil.get_tree(url, proxy_url=SystemModelSetting.get('site_daum_proxy'), headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            for xpath in ['//*[@id="prfColl"]/div/div/div/div[2]/div[2]/div[1]/span[2]', '//*[@id="prfColl"]/div/div/div/div[2]/div/div/span[2]']:
                tags = root.xpath(xpath)
                if tags:
                    tmp = tags[0].text_content()
                    #logger.debug(tmp)
                    tmps = tmp.split(',')
                    if len(tmps) == 1:
                        ret = [tmps[0].strip()]
                    else:
                        ret = [x.strip() for x in tmps]
                    #일본배우땜에
                    ret2 = []
                    for x in ret:
                        ret2.append(x)
                        tmp = x.split(' ')
                        if len(tmp) == 2:
                            ret2.append('%s %s' % (tmp[1], tmp[0]))

                    return ret2
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
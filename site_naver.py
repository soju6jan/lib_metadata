
# -*- coding: utf-8 -*-


import requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html


from framework import SystemModelSetting, py_urllib, py_urllib2
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite


from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemMovie, EntityMovie2
from .site_util import SiteUtil

logger = P.logger


class SiteNaver(object):
    site_name = 'naver'
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }


class SiteNaverMovie(SiteNaver):
    site_base_url = 'https://movie.naver.com'
    module_char = 'M'
    site_char = 'N'


    @classmethod 
    def search(cls, keyword, year=1900):
        try:
            ret = {}
            logger.debug(keyword)
            data = cls.naver_api_search(keyword)
            logger.debug(json.dumps(data, indent=4))
            result_list = []
            for idx, item in enumerate(data['items']):
                entity = EntitySearchItemMovie(cls.site_name)
                entity.code = cls.module_char + cls.site_char + item['link'].split('=')[1]
                entity.title = re.sub(r'\<.*?\>', '', item['title']).strip()
                entity.originaltitle = re.sub(r'\<.*?\>', '', item['subtitle']).strip()
                entity.image_url = item['image']
                entity.year = int(item['pubDate'])
                if item['actor'] != '':
                    entity.desc += u'배우 : %s\r\n' % ', '.join(item['actor'].rstrip('|').split('|'))
                if item['director'] != '':
                    entity.desc += u'감독 : %s\r\n' % ', '.join(item['director'].rstrip('|').split('|'))
                if item['userRating'] != '0.00':
                    entity.desc += u'평점 : %s\r\n' % item['userRating']

                # etc
                entity.extra_info['actor'] = item['actor']
                entity.extra_info['director'] = item['director']
                entity.extra_info['userRating'] = item['userRating']

                if SiteUtil.compare(keyword, entity.title) or SiteUtil.compare(keyword, entity.originaltitle):
                    if year != 1900:
                        if year == entity.year:
                            entity.score = 100
                        elif abs(entity.year-year) == 1:
                            entity.scroe = 90
                        else:
                            entity.score = 80
                    else:
                        entity.score = 95
                else:
                    entity.score = 80 - (idx*5)
                result_list.append(entity.as_dict())

            if result_list is None:
                ret['ret'] = 'empty'
            else:
                ret['ret'] = 'success'
                ret['data'] = result_list
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret

        

    @classmethod
    def naver_api_search(cls, keyword, source='ja', target='ko'):
        trans_papago_key = SystemModelSetting.get_list('trans_papago_key')
        for tmp in trans_papago_key:
            client_id, client_secret = tmp.split(',')
            try:
                if client_id == '' or client_id is None or client_secret == '' or client_secret is None: 
                    return text
                url = "https://openapi.naver.com/v1/search/movie.json?query=%s" % py_urllib.quote(str(keyword))
                requesturl = py_urllib2.Request(url)
                requesturl.add_header("X-Naver-Client-Id", client_id)
                requesturl.add_header("X-Naver-Client-Secret", client_secret)
                #response = py_urllib2.urlopen(requesturl, data = data.encode("utf-8"))
                response = py_urllib2.urlopen(requesturl)
                data = json.load(response, encoding="utf-8")
                rescode = response.getcode()
                if rescode == 200:
                    return data
                else:
                    continue
            except Exception as exception:
                logger.error('Exception:%s', exception)
                logger.error(traceback.format_exc())                
        



    @classmethod 
    def info(cls, code):
        try:
            ret = {}
            entity = EntityMovie2(cls.site_name, code)
            url = 'https://movie.naver.com/movie/bi/mi/basic.nhn?code=%s' % code[2:]

            logger.debug(url)
            root = html.fromstring(requests.get(url).text)

            tags = root.xpath('//div[@class="mv_info"]')
            #logger.debug(html.tostring(tags[0]))
            if tags:
                entity.title = tags[0].xpath('.//h3/a')[0].text_content()
                entity.title_ko = entity.title
                tmp = tags[0].xpath('.//strong')[0].text_content()
                tmps = [x.strip() for x in tmp.split(',')]
                if len(tmps) == 2:# 영문제목, 년도
                    entity.title_en = tmps[0]
                    entity.year = int(tmps[1])
                elif len(tmps) == 3: # 일문,한문 / 영문 / 년도
                    entity.title_3 = tmps[0]
                    entity.title_en = tmps[1]
                    entity.year = int(tmps[2])
                else:
                    logger.debug('TTTTTOOOOOODDDDOOO')


            tags = root.xpath('//div[@class="main_score"]')
            if tags:
                tmp_tag = tags[0].xpath('.//*[@id="actualPointPersentWide"]//em')
                if tmp_tag:
                    tmp = ''.join([x.text for x in tmp_tag])
                    logger.debug(tmp)
                    try: entity.ratings.append(EntityRatings(float(tmp), name='naver'))
                    except: pass

            tags = root.xpath('//p[@class="info_spec"]')
            if tags:
                tags = tags[0].xpath('.//span')
                info_list = []
                for tag in tags:
                    tmp_tag = tag.xpath('.//a')
                    if tmp_tag:
                        info_list.append(tmp_tag[0].text_content().strip())
                    else:
                        logger.debug(tag.text)
                        info_list.append(tag.text)

                logger.debug(info_list)
            
            for x in info_list:
                logger.debug(x)


            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()
            return ret

            show = EntityShow(cls.site_name, code)

            # 종영와, 방송중이 표현 정보가 다르다. 종영은 studio가 없음
            url = 'https://search.daum.net/search?w=tv&q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(str(title)), code[2:])
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            home_url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(str(title)), code[2:])

            logger.debug(home_url)
            home_root = SiteUtil.get_tree(home_url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            home_data = cls.get_show_info_on_home(home_root)

            logger.debug('home_datahome_datahome_datahome_datahome_datahome_datahome_datahome_datahome_data')
            logger.debug(home_data)

            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/strong')
            if len(tags) == 1:
                show.title = tags[0].text_content().strip()
                show.originaltitle = show.title
                show.sorttitle = show.title #unicodedata.normalize('NFKD', show.originaltitle)
                logger.debug(show.sorttitle)
            
            show.studio = home_data['studio']
            show.plot = home_data['desc']
            match = re.compile(r'(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})').search(home_data['broadcast_term'])
            if match:
                show.premiered = match.group('year') + '-' + match.group('month').zfill(2) + '-'+ match.group('day').zfill(2)
                show.year = int(match.group('year'))
            show.status = home_data['status']
            show.genre = [home_data['genre']]
            show.episode = home_data['episode']

            tmp = root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')
            logger.debug(tmp)


            show.thumb.append(EntityThumb(aspect='poster', value=cls.process_image_url(root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src']), site='daum', score=-10))


            

            for i in range(1,3):
                items = root.xpath('//*[@id="tv_casting"]/div[%s]/ul//li' % i)
                logger.debug('CASTING ITEM LEN : %s' % len(items))
                for item in items:
                    actor = EntityActor(None)
                    cast_img = item.xpath('div/a/img')
                    if len(cast_img) == 1:
                        actor.thumb = cls.process_image_url(cast_img[0].attrib['src'])
                    
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
                logger.debug(show.extra_info['kakao_id'])

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


"""

# 검색어 인코딩 모르겠음            
            #url = 'https://movie.naver.com/movie/search/result.nhn?section=movie&query=%s' % (py_urllib.quote(str(keyword)))
            # 검색어 입력시 쿼리
            #url = 'https://auto-movie.naver.com/ac?q_enc=UTF-8&st=1&r_lt=1&n_ext=1&t_koreng=1&r_format=json&r_enc=UTF-8&r_unicode=0&r_escape=1&q=%s' % (py_urllib.quote(str(keyword)))
           


    https://movie.naver.com/movie/bi/mi/photoListJson.nhn?movieCode=163834

    /movie/bi/mi/photoListJson.nhn?movieCode=163834

    https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/51B0F09D48A30832A07852CAE57980AD4B0E?key=V128838cfd0a24b85045ee02f448c29271f6049df361acf3aeebbe45e3bcba02885c7e02f448c29271f60&pid=rmcPlayer_16107273668922215&sid=2003&ver=2.0&devt=html5_pc&doct=json&ptc=https&sptc=https&cpt=vtt&ctls=%7B%22visible%22%3A%7B%22fullscreen%22%3Atrue%2C%22logo%22%3Atrue%2C%22playbackRate%22%3Afalse%2C%22scrap%22%3Afalse%2C%22playCount%22%3Atrue%2C%22commentCount%22%3Atrue%2C%22title%22%3Atrue%2C%22writer%22%3Atrue%2C%22expand%22%3Afalse%2C%22subtitles%22%3Atrue%2C%22thumbnails%22%3Atrue%2C%22quality%22%3Atrue%2C%22setting%22%3Atrue%2C%22script%22%3Afalse%2C%22logoDimmed%22%3Atrue%2C%22badge%22%3Atrue%2C%22seekingTime%22%3Atrue%2C%22muted%22%3Atrue%2C%22muteButton%22%3Afalse%2C%22viewerNotice%22%3Afalse%2C%22linkCount%22%3Afalse%2C%22createTime%22%3Afalse%2C%22thumbnail%22%3Atrue%7D%2C%22clicked%22%3A%7B%22expand%22%3Afalse%2C%22subtitles%22%3Afalse%7D%7D&pv=4.17.48&dr=3072x1728&lc=ko_KR


    https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/51B0F09D48A30832A07852CAE57980AD4B0E?key=V128838cfd0a24b85045ee02f448c29271f6049df361acf3aeebbe45e3bcba02885c7e02f448c29271f60


    https://movie.naver.com/movie/bi/mi/videoPlayer.nhn?code=163834&type=movie&videoId=51B0F09D48A30832A07852CAE57980AD4B0E&videoInKey=V127b9107ee229f6ce232e02f448c29271f6049df361acf3aeebbe45e3bcba02885c7e02f448c29271f60


    
        
        	
			if(location.pathname == "/movie/bi/mi/mediaView.nhn"){
                var oMediaView = new nhn.movie.end.MediaView(jindo.$('_MediaView'), {
                    nListDisplaySize: oViewMode.is('basic') ? 4 : 8,
                    sListApiUrl: '/movie/bi/mi/videoListJson.nhn?movieCode=163834',
                    sVideoInfoApiUrl: '/movie/bi/mi/videoInfoJson.nhn',
                    sVideoUrlTpl: '/movie/bi/mi/videoPlayer.nhn?code=163834&type=movie&videoId={=videoId}&videoInKey={=videoInKey}&coverImage={=coverImage}&mid={=multimediaId}&autoPlay=true&playerSize=665x480'
                }).attach('itemshow', function (oEvent) {
                    // NDS
                    try {
                        lcs_do();
                    } catch(e){}
                });
                oViewMode.attach('change', function (oEvent) {
                    if (oEvent.sStyle === 'basic') {
                        oMediaView.option('nListDisplaySize', 4);
                    } else {
                        oMediaView.option('nListDisplaySize', 8);
                    }
                    oMediaView.update();
                });
			}


"""

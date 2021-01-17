
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


# https://developers.naver.com/docs/search/movie/

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

                logger.debug(year)
                logger.debug(entity.year)
                logger.debug(keyword)
                logger.debug(entity.title)

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
            
            cls.info_basic(code, entity)
            cls.info_detail(code, entity)
            cls.info_photo(code, entity)

            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()
            return ret


        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret




    @classmethod 
    def info_photo(cls, code, entity):
        try:
            page = 1
            while True:
                url = 'https://movie.naver.com/movie/bi/mi/photoListJson.nhn?movieCode=%s&size=100&offset=%s' % (code[2:], (page-1)*100)
                data = requests.get(url).json()['lists']
                
                poster_count = 0
                art_count = 0
                max_poster_count = 5
                max_art_count = 10
                base_score  = 60
                for item in data:
                    art = EntityThumb()
                    if item['imageType'] == 'STILLCUT':
                        if art_count >= max_art_count:
                            continue
                        art.aspect = 'landscape'
                        art.score = base_score - 10 - art_count
                        art_count += 1
                    elif item['imageType'] == 'POSTER':
                        if poster_count >= max_art_count:
                            continue
                        if item['width'] > item['height']:
                            art.aspect = 'landscape'
                            art.score = base_score + max_art_count - art_count
                            art_count += 1
                        else:
                            art.aspect = 'poster'
                            art.score = base_score - poster_count
                            poster_count += 1
                    else:
                        continue
                    art.value = item['fullImageUrl']
                    art.thumb = item['fullImageUrl221px']
                    entity.art.append(art)
                page += 1
                if len(data) != 100 or page > 3:
                    break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


            #https://search.pstatic.net/common/?src=https%3A%2F%2Fssl.pstatic.net%2Fsstatic%2Fpeople%2Fportrait%2F201701%2F20170112145759747-9836275.jpg&type=u111_139&quality=95

            # https://ssl.pstatic.net/sstatic/people/portrait/201701/20170112145759747-9836275.jpg



    @classmethod 
    def info_detail(cls, code, entity):
        try:
            #https://movie.naver.com/movie/bi/mi/detail.nhn?code=182205

            url = 'https://movie.naver.com/movie/bi/mi/detail.nhn?code=%s' % code[2:]
            logger.debug(url)
            root = html.fromstring(requests.get(url).text)

            tags = root.xpath('//ul[@class="lst_people"]/li')
            if tags:
                for tag in tags:
                    actor = EntityActor('', site=cls.site_name)
                    tmp = tag.xpath('.//img')[0].attrib['src']
                    
                    match = re.search(r'src\=(?P<url>.*?)\&', tmp) 
                    if match:
                        actor.thumb = py_urllib.unquote(match.group('url'))
                    
                    actor.name = tag.xpath('.//div[@class="p_info"]/a')[0].attrib['title']
                    actor.role = tag.xpath('.//div[@class="p_info"]//p[@class="pe_cmt"]/span')[0].text_content().replace(u'역', '').strip()
                    entity.actor.append(actor)
            
            tags = root.xpath('//div[@class="director"]//div[@class="dir_obj"]')
            if tags:
                for tag in tags:
                    tmp = tag.xpath('.//div[@class="dir_product"]/a')[0].attrib['title']
                    entity.director.append(tmp)

            tags = root.xpath('//div[@class="staff"]//tr[1]//span')
            if tags:
                for tag in tags:
                    tmp = tag.xpath('.//a')[0].text_content()
                    entity.credits.append(tmp) 
            
            tags = root.xpath('//div[@class="agency"]/dl')
            if tags:
                tmp1 = tags[0].xpath('.//dt')
                tmp2 = tags[0].xpath('.//dd')
                for idx, tag in enumerate(tmp1):
                    if tag.text_content().strip() == u'제작':
                        entity.studio = tmp2[idx].text_content().strip()
                        break
                    

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


            #https://search.pstatic.net/common/?src=https%3A%2F%2Fssl.pstatic.net%2Fsstatic%2Fpeople%2Fportrait%2F201701%2F20170112145759747-9836275.jpg&type=u111_139&quality=95

            # https://ssl.pstatic.net/sstatic/people/portrait/201701/20170112145759747-9836275.jpg



    @classmethod 
    def info_basic(cls, code, entity):
        try:
            url = 'https://movie.naver.com/movie/bi/mi/basic.nhn?code=%s' % code[2:]
            logger.debug(url)
            root = html.fromstring(requests.get(url).text)

            tags = root.xpath('//div[@class="mv_info"]')
            #logger.debug(html.tostring(tags[0]))
            if tags:
                entity.title = tags[0].xpath('.//h3/a')[0].text_content()
                entity.extra_info['title_ko'] = entity.title
                tmp = tags[0].xpath('.//strong')[0].text_content()
                tmps = [x.strip() for x in tmp.split(',')]
                if len(tmps) == 2:# 영문제목, 년도
                    entity.extra_info['title_en'] = tmps[0]
                    entity.year = int(tmps[1])
                elif len(tmps) == 3: # 일문,한문 / 영문 / 년도
                    entity.extra_info['title_3'] = tmps[0]
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

                for tag in tags:
                    a_tag = tag.xpath('.//a')
                    if a_tag:
                        href = a_tag[0].attrib['href']
                        if href.find('genre=') != -1:
                            for tmp in a_tag:
                                entity.genre.append(tmp.text_content().strip())
                        elif href.find('nation=') != -1:
                            tmp = a_tag[0].text_content().strip()
                            entity.country.append(tmp)
                            if tmp == u'한국':
                                entity.originaltitle = entity.extra_info['title_ko']
                            else:
                                entity.originaltitle = entity.extra_info['title_3'] if entity.title_3 != '' else entity.extra_info['title_en'] 

                        elif href.find('open=') != -1:
                            entity.premiered = (a_tag[0].text_content().strip() + a_tag[1].text_content().strip()).replace('.', '-')
                            entity.year = int(entity.premiered.split('-')[0])
                        elif href.find('grade=') != -1:
                            entity.mpaa = a_tag[0].text_content().strip()
                    else:
                        if tag.text_content().find(u'분') != -1:
                            entity.runtime = int(tag.text_content().replace(u'분', '').strip())

            tags = root.xpath('//div[@class="story_area"]//h5[@class="h_tx_story"]')
            if tags:
                entity.tagline = tags[0].text_content().strip()
            
            tags = root.xpath('//div[@class="story_area"]//p[@class="con_tx"]/text()')
            if tags:
                entity.plot = '\r\n'.join([tag.strip().replace('&nbsp;', '') for tag in tags])
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())













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

EFY7W9W6T70TM13GKUGZ
https://www.kmdb.or.kr/mypage/api/1034
https://www.kmdb.or.kr/info/api/apiDetail/6

기본 요청 URL : http://api.koreafilm.or.kr/openapi-data2/wisenut/search_api/search_xml2(또는 search_json2).jsp?collection=kmdb_new2
예시) http://api.koreafilm.or.kr/openapi-data2/wisenut/search_api/search_xml2.jsp?collection=kmdb_new2&detail=N&director=%EB%B0%95%EC%B0%AC%EC%9A%B1&ServiceKey=인증키값

"""

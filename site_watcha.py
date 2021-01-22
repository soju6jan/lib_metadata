
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
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemMovie, EntityMovie2, EntityExtra2, EntityReview
from .site_util import SiteUtil

logger = P.logger


class SiteWatcha(object):
    site_name = 'watcha'
    
    default_headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        #'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        #'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'x-watchaplay-client': 'WatchaPlay-WebApp',
        'x-watchaplay-client-language': 'ko',
        'x-watchaplay-client-region' : 'KR',
        'x-watchaplay-client-version' : '1.0.0',
        'referer': 'https://pedia.watcha.com/',
        'origin': 'https://pedia.watcha.com',
        'x-watcha-client': 'watcha-WebApp',
        'x-watcha-client-language': 'ko',
        'x-watcha-client-region': 'KR',
        'x-watcha-client-version': '2.0.0',
    }

    """
    default_headers = {
        #'accept': 'application/vnd.frograms+json;version=20',
        #'accept-encoding': 'gzip, deflate, br',
        #'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        #'cookie': 'G_ENABLED_IDPS=google; _s_guit=2c38af244878e5e28e3193052db5d0d396eb2229ed394bf9a87e2eeb406a; _c_pm=false; wp_attcn:ZBm5R18Y7vd46=[{"audio":"","subtitle":"none"},{"audio":"ko","subtitle":"none"}]; _c_pv=0.9; _c_lattpp=1611199449215; _gid=GA1.2.1565107000.1611199454; _ga_1PYHGTCRYW=GS1.1.1611221002.5.1.1611221606.0; _guinness_session=ZQgDghUno%2BqpfsWIdAa8Vofq0k0V5H5XB%2BEUzGI4dBg83pl2YEAzGMFh5WOHGONl%2F37WMOpeU%2Bc%2FS8dDmKuHo%2FWn--xPj6Wi7WxVa5tyAF--tTqhPEh2A7dA8oUXNlm4aQ%3D%3D; _ga_1PF16G1LBX=GS1.1.1611220995.15.1.1611221695.0; _ga_KJMWF42C8H=GS1.1.1611220995.16.1.1611221695.0; _ga=GA1.1.1062148787.1610196018',
        #'origin': 'https://pedia.watcha.com',
        #'referer': 'https://pedia.watcha.com/',
        #'sec-ch-ua': '"Google Chrome";v="87", " Not;A Brand";v="99", "Chromium";v="87"',
        #'sec-ch-ua-mobile': '?0',
        #'sec-fetch-dest': 'empty',
        #'sec-fetch-mode': 'cors',
        #'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
        'x-watcha-client': 'watcha-WebApp',
        'x-watcha-client-language': 'ko',
        'x-watcha-client-region': 'KR',
        'x-watcha-client-version': '2.0.0',
        #'x-watcha-remote-addr': '',
    }
    cookies = {'G_ENABLED_IDPS':'google', '_s_guit':'2c38af244878e5e28e3193052db5d0d396eb2229ed394bf9a87e2eeb406a', '_c_pm':'false', 'wp_attcn:ZBm5R18Y7vd46':'[{"audio":"","subtitle":"none"},{"audio":"ko","subtitle":"none"}]', '_c_pv':'0.9', '_c_lattpp':'1611199449215', '_gid':'GA1.2.1565107000.1611199454', '_ga_1PF16G1LBX':'GS1.1.1611199453.14.1.1611199559.0', '_ga_KJMWF42C8H':'GS1.1.1611199453.15.1.1611199559.0', '_ga':'GA1.1.1062148787.1610196018', '_ga_1PYHGTCRYW':'GS1.1.1611203000.4.1.1611203338.0', '_guinness_session':'S17q5ecj6sVxMS4rvFpLxvoQFJSqRCFp5rKRtTVhM4%2Bjtiq1cEsPF01OBXjK%2FxLzb0Zqn4SuQMDR0FXt9J4oZb8%2B--n9fzFfU61x6mtrh6--IBwOAYjjYYLki%2FDy4aHTfA%3D%3D'}
    """

# https://developers.naver.com/docs/search/movie/

class SiteWatchaMovie(SiteWatcha):
    #site_base_url = 'https://movie.naver.com'
    module_char = 'M'
    site_char = 'W'

    @classmethod
    def search_api(cls, keyword):
        try:
            url = 'https://api-pedia.watcha.com/api/searches?query=%s' % keyword
            data = SiteUtil.get_response(url, headers=cls.default_headers).json()
            return data
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def info_api(cls, code):
        try:
            if code.startswith(cls.module_char + cls.site_char):
                code = code[2:]
            ret = {}
            ret['review'] = cls.info_review(code, None, api_return=True)
            ret['collection'] = cls.info_collection(code, None, api_return=True)
            return ret
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod 
    def search(cls, keyword, year=1900):
        try:
            ret = {}
            #url = 'https://api-mars.watcha.com/api/search.json?query=%s&page=1&per=30&exclude=limited' % keyword
            
            data = cls.search_api(keyword)
            
            
            result_list = []
            for idx, item in enumerate(data['result']['top_results']):
                if item['content_type'] != 'movies':
                    continue
                #logger.debug(json.dumps(item, indent=4))
                entity = EntitySearchItemMovie(cls.site_name)
                entity.code = cls.module_char + cls.site_char + item['code']
                entity.title = item['title']
                #logger.debug(entity.title)
                #entity.originaltitle = re.sub(r'\<.*?\>', '', item['subtitle']).strip()
                #entity.extra_info['title_en'] = item['eng_title']
                if 'poster' in item and item['poster'] is not None:
                    entity.image_url = item['poster']['original']
                entity.year = item['year']
                #except: entity.year = 1900
                entity.desc = item['nations'][0]['name']

                if SiteUtil.compare(keyword, entity.title):
                    if year != 1900:
                        if year == entity.year:
                            entity.score = 100
                        elif abs(entity.year-year) == 1:
                            entity.score = 90 - idx
                        else:
                            entity.score = 80 - idx
                    else:
                        entity.score = 95 - idx
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
    def info(cls, code):
        try:
            #https://api-mars.watcha.com/api/contents/mdMgQaX.json
            ret = {}
            entity = EntityMovie2(cls.site_name, code)
            
            if code.startswith(cls.module_char + cls.site_char):
                code = code[2:]
            entity.code_list.append(['watcha_id', code])
            #url = 'https://api-pedia.watcha.com/api/contents/%s/comments?filter=all&order=popular&page=1&size=5' % code
            #url = 'https://api-mars.watcha.com/api/contents/%s.json' % code
            #data = SiteUtil.get_response(url, headers=cls.default_headers).json()
            #if 'msg' in data:
            #    logger.debug(data['msg'])

            #logger.debug(json.dumps(data, indent=4))
            cls.info_review(code, entity)
            cls.info_collection(code, entity)
            
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
    def info_review(cls, code, entity, api_return=False):
        try:
            url = 'https://api-pedia.watcha.com/api/contents/%s/comments?filter=all&order=popular&page=1&size=8' % code
            data = SiteUtil.get_response(url, headers=cls.default_headers).json()
            if api_return:
                return data

            for item in data['result']['result']:
                review = EntityReview(cls.site_name)
                review.text = u'[좋아요 : %s' % item['likes_count']
                review.source = ''
                review.author = item['user']['name']
                if item['user_content_action']['rating'] is not None:
                    review.text += ' / 평점 : %s' % (item['user_content_action']['rating']/2.0)
                    review.rating = item['user_content_action']['rating']
                review.link = ''
                review.text += ']   ' + item['text'].replace('\n', '\r\n')
                entity.review.append(review)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod 
    def info_collection(cls, code, entity, api_return=False):
        try:
            url = 'https://api-pedia.watcha.com/api/contents/%s/decks?page=1&size=10' % code
            data = SiteUtil.get_response(url, headers=cls.default_headers).json()
            if api_return:
                return data

            #logger.debug(json.dumps(data, indent=4))
            for item in data['result']['result']:
                #logger.debug(item['likes_count'])
                if item['likes_count'] > 100:
                    entity.tag.append(item['title'])
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())









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
                    tmp = tag.xpath('.//div[@class="p_info"]/em')
                    if tmp:
                        actor.originalname = tmp[0].text_content()
                    tmp = tag.xpath('.//div[@class="p_info"]//p[@class="pe_cmt"]/span')
                    if tmp:
                        actor.role = tmp[0].text_content().replace(u'역', '').strip()
                    entity.actor.append(actor)
            
            tags = root.xpath('//div[@class="director"]//div[@class="dir_obj"]')
            if tags:
                for tag in tags:
                    tmp = tag.xpath('.//div[@class="dir_product"]/a')
                    if tmp:
                        entity.director.append(tmp[0].attrib['title'])

            #
            tags = root.xpath('//div[@class="staff"]//tr[1]//span')
            if tags:
                for tag in tags:
                    tmp = tag.xpath('.//a')
                    if tmp:
                        entity.credits.append(tmp[0].text_content().strip()) 
                    else:
                        entity.credits.append(tag.text.strip()) 
            
            tags = root.xpath('//div[@class="agency"]/dl')
            if tags:
                tmp1 = tags[0].xpath('.//dt')
                tmp2 = tags[0].xpath('.//dd')
                for idx, tag in enumerate(tmp1):
                    if tag.text_content().strip() == u'제작':
                        tmp = tmp2[idx].xpath('.//a')
                        entity.studio = tmp[0].text_content().strip() if tmp else tmp2[idx].text_content().strip()
                    

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
                """
                tmp_tag = tags[0].xpath('.//*[@id="actualPointPersentWide"]//em')
                if tmp_tag:
                    tmp = ''.join([x.text for x in tmp_tag])
                    logger.debug(tmp)
                    try: entity.ratings.append(EntityRatings(float(tmp), name='naver'))
                    except: pass
                """
                tmp_tag = tags[0].xpath('.//*[@id="pointNetizenPersentWide"]//em')
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
                                entity.originaltitle = entity.extra_info['title_3'] if 'title_3' in entity.extra_info else entity.extra_info['title_en'] 

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
            
            """
            tags = root.xpath('//div[@class="making_note"]/p/text()')
            if tags:
                entity.extra_info['making_note'] = '\r\n'.join([tag.strip().replace('&nbsp;', '') for tag in tags])
            """
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod 
    def get_video_url(cls, param):
        try:
            tmps = param.split(',')
            #tab
            url = 'https://movie.naver.com/movie/bi/mi/mediaView.nhn?code=%s&mid=%s' % (tmps[0][2:], tmps[1])
            root = html.fromstring(requests.get(url).text)
            tmp = root.xpath('//iframe[@class="_videoPlayer"]')[0].attrib['src']

            #logger.debug(tmp)

            match = re.search(r'&videoId=(.*?)&videoInKey=(.*?)&', tmp)
            #logger.debug(match.group(0))
            #logger.debug(match.group(1))
            #logger.debug(match.group(2))
            
            if match:
                url = 'https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/%s?key=%s' % (match.group(1), match.group(2))

                #logger.debug(url)
                data = requests.get(url).json()
                #logger.debug(data)
                ret = data['videos']['list'][0]['source']
                return ret
            #https://movie.naver.com/movie/bi/mi/videoPlayer.nhn?code=178544&type=movie&videoId=90A76F8E51A5983F599D4F3D181E67D1BF1E&videoInKey=V1215256d6ef321c91abd57707f7ce007402b199379c36ed70f7cf563abf4d47a7af557707f7ce007402b&coverImage=/multimedia/MOVIECLIP/TRAILER/43106_cover_20190723100158.jpg&mid=43106&autoPlay=true&playerSize=665x480


            #https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/90A76F8E51A5983F599D4F3D181E67D1BF1E?key=V124678127e443a0598d257707f7ce007402b199379c36ed70f7cf563abf4d47a7af557707f7ce007402b

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


https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/90A76F8E51A5983F599D4F3D181E67D1BF1E?key=V124678127e443a0598d257707f7ce007402b199379c36ed70f7cf563abf4d47a7af557707f7ce007402b

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

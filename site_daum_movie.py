
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
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemMovie, EntityMovie2, EntityExtra2
from .site_util import SiteUtil
from .site_daum import SiteDaum

logger = P.logger


class SiteDaumMovie(SiteDaum):
    
    site_base_url = 'https://search.daum.net'
    module_char = 'M'
    site_char = 'D'


    @classmethod 
    def search(cls, keyword, year=1900):
        try:
            ret = {}
            result_list = cls.search_movie_api(keyword, year)
            result_list = list(reversed(sorted(result_list, key=lambda k:k['score'])))
            if result_list is None:
                ret['ret'] = 'empty'
            else:
                ret['ret'] = 'success'
                ret['data'] = result_list
            return ret
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret



    @classmethod
    def search_movie_api(cls, keyword, year):
        try:
            ret = []
            url = f"https://movie.daum.net/api/search?q={py_urllib.quote(str(keyword))}&t=movie&page=1&size=20"
            data = requests.get(url).json()
            for idx, item in enumerate(data['result']['search_result']['documents']):
                item = item['document']
                logger.debug(item)
                if idx > 5:
                    break
                entity = EntitySearchItemMovie(cls.site_name)
                entity.title = item['titleKoreanHanl']
                entity.code = cls.module_char + cls.site_char + item['movieId']
                entity.image_url = item['mainPhoto']
                entity.year = item['productionYear']
                entity.extra_info['title_en'] = item['titleEnglishHanl']
                entity.desc = f"{item['admission']} / {item['genres']}"

                if SiteUtil.compare(keyword, entity.title) or (item['titleEnglishHanl'] != '' and SiteUtil.compare(keyword, item['titleEnglishHanl'])) or (item['titleAdminHanl'] != '' and SiteUtil.compare(keyword, item['titleAdminHanl'])):
                    if year != 1900:
                        if abs(entity.year-year) <= 1:
                            entity.score = 100
                        else:
                            entity.score = 80
                    else:
                        entity.score = 95
                else:
                    entity.score = 80 - (idx*5)
                if entity.score < 10:
                    entity.score = 10
                ret.append(entity.as_dict())
            return ret
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    



    @classmethod 
    def info_api(cls, code):
        try:
            ret = {'ret':'success', 'data':{}}
            url = "https://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s" % code[2:]
            ret['data']['basic'] = requests.get(url).json()['data']

            url = "https://movie.daum.net/data/movie/movie_info/cast_crew.json?movieId=%s" % code[2:]
            ret['data']['cast'] = requests.get(url).json()['data']

            url = "https://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s" % code[2:]
            ret['data']['photo'] = requests.get(url).json()['data']

            url = 'https://movie.daum.net/moviedb/videolist.json?id=%s&page=%s' % (code[2:], '1')
            ret['data']['video'] = requests.get(url).json()
            return ret
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret

   

    @classmethod 
    def info(cls, code):
        try:
            ret = {}
            entity = EntityMovie2(cls.site_name, code)
            entity.code_list.append(['daum_id', code[2:]])
            cls.info_basic(code, entity)
            #cls.info_cast(code, entity)
            cls.info_photo(code, entity)
            cls.info_video(code, entity)
            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()
            return ret


        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret
    
        
    # 2021-04-15 
    @classmethod
    def info_basic(cls, code, entity):
        try:
            url = "https://movie.daum.net/api/movie/%s/main" % code[2:]
            data = requests.get(url).json()
            entity.title = data['movieCommon']['titleKorean']
            entity.originaltitle = data['movieCommon']['titleEnglish']
            entity.year = data['movieCommon']['productionYear']
            tmp = data['movieCommon']['plot']
            if tmp is None:
                entity.plot = ''
            else:
                entity.plot = tmp.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
            try: entity.ratings.append(EntityRatings(float(data['movieCommon']['avgRating']), name=cls.site_name))
            except: pass
            entity.country = data['movieCommon']['productionCountries']
            entity.genre = data['movieCommon']['genres']
            if len(data['movieCommon']['countryMovieInformation']) > 0:
                for country in data['movieCommon']['countryMovieInformation']:
                    if country['country']['id'] == 'KR':
                        entity.mpaa = country['admissionCode']
                        entity.runtime = country['duration']
                        tmp = country['releaseDate']
                        if tmp is not None:
                            entity.premiered = tmp[0:4] + '-' + tmp[4:6] + '-' + tmp[6:8]
                        break
            if data['movieCommon']['mainPhoto'] is not None:
                entity.art.append(EntityThumb(aspect='poster', value=data['movieCommon']['mainPhoto']['imageUrl'], site=cls.site_name, score=70))

            for cast in data['casts']:
                actor = EntityActor('', site=cls.site_name)
                actor.thumb = cast['profileImage']
                actor.name = cast['nameKorean']
                actor.originalname = cast['nameEnglish']
                actor.role = cast['description']
                if actor.role is None:
                    actor.role = cast['movieJob']['job']
                if cast['movieJob']['job'] == u'감독':
                    entity.director.append(actor.name)
                else:
                    entity.actor.append(actor)
            if 'staff' in data:
                for cast in data['staff']:
                    if cast['movieJob']['role'] == u'각본':
                        entity.credits.append(cast['nameKorean'])
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    #https://movie.daum.net/api/movie/124084/main
    #https://movie.daum.net/api/movie/124084/crew
    """
    @classmethod
    def info_basic(cls, code, entity):
        try:
            url = "https://movie.daum.net/moviedb/main?movieId=%s" % code[2:]
            logger.debug(url)
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            tags = root.xpath('//h3[@class="tit_movie"]/span[@class="txt_tit"]')
            if tags:
                entity.title = tags[0].text_content().strip()

            tags = root.xpath('//div[@class="head_origin"]/span[@class="txt_name"]')
            if tags:
                tmp = tags[0].text_content().strip().split(',')
                if len(tmp) == 2:
                    entity.extra_info['title_en'] = tmp[0].strip()
                    entity.originaltitle = tmp[0].strip()
                    entity.year = int(tmp[1].strip())
                elif len(tmp) > 2:
                    title_en = ','.join(tmp[:-1])
                    entity.extra_info['title_en'] = title_en
                    entity.originaltitle = title_en
                    entity.year = int(tmp[-1].strip())
                elif len(tmp) == 1:
                    entity.extra_info['title_en'] = entity.originaltitle = ''
                    try: entity.year = int(tmp[0].strip())
                    except: pass


            tags = root.xpath('//dl[@class="list_cont"]')
            logger.debug(tags)
            if tags:
                for tag in tags:
                    key = tag.xpath('.//dt')[0].text_content().strip()
                    value = tag.xpath('.//dd')[0].text_content().strip()
                    #logger.debug('%s:%s', key, value)
                    if key in [u'개봉', u'공개']:
                        entity.premiered = value.replace('.', '-')
                    elif key == u'장르':
                        entity.genre = value.split('/')
                    elif key == u'국가':
                        entity.country = [x.strip() for x in value.split(',')]
                    elif key == u'등급':
                        entity.mpaa = value
                    elif key == u'러닝타임':
                        match = re.compile(r'(?P<min>\d+)%s' % u'분').match(value)
                        if match:
                            entity.runtime = int(match.group('min'))
                        else:
                            entity.runtime = ''
                    elif key == u'평점':
                        try: entity.ratings.append(EntityRatings(float(value), name=cls.site_name))
                        except: pass

            tags = root.xpath('//a[@class="thumb_img"]/span[@class="bg_img"]')
            logger.debug(tags)
            if tags:
                tmp = tags[0].attrib['style']
                tmp = tmp.split('(')[1].split(')')[0]
                entity.art.append(EntityThumb(aspect='poster', value=cls.process_image_url(tmp), site=cls.site_name, score=70))

            tags = root.xpath('//div[@class="movie_summary"]')
            logger.debug(tags)
            if tags:
                all_plot = tags[0].text_content().strip()
                tags = root.xpath('//div[@class="desc_cont"]/div[@class="making_note"]')
                if tags:
                    tmp2 = tags[0].text_content().strip()
                    all_plot = all_plot.replace(tmp2, '').strip()
                entity.plot = all_plot.strip()
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())



    @classmethod
    def info_cast(cls, code, entity):
        try:
            url = "https://movie.daum.net/moviedb/crew?movieId=%s" % code[2:]
            logger.debug(url)
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            tags = root.xpath('//div[@class="item_crew"]')
            for tag in tags:
                actor = EntityActor('', site=cls.site_name)
                img_tag = tag.xpath('.//img') 
                if img_tag:
                    actor.thumb = cls.process_image_url(img_tag[0].attrib['src'])
                tmp = tag.xpath('.//strong[@class="tit_item"]')
                if tmp:
                    tmp2 = tmp[0].xpath('.//a')
                    if tmp2:
                        actor.name = tmp2[0].text_content().strip()
                    tmp2 = tag.xpath('.//span[@class="subtit_item"]')
                    if tmp2:
                        actor.originalname = tmp2[0].text_content().strip()
                    tmp2 = tag.xpath('.//span[@class="txt_info"]')
                    if tmp2:
                        actor.role = tmp2[0].text_content().strip().replace(u'역', '')

                if actor.role == '감독':
                    entity.director.append(actor.name)
                else:
                    entity.actor.append(actor)

            divs = root.xpath('//div[@class="detail_produceinfo"]')
            for div in divs:
                div_name = div.xpath('.//h5[@class="tit_section"]')[0].text_content()
                tags = div.xpath('.//dl[@class="list_produce"]')
                for tag in tags:
                    key = tag.xpath('.//dt')[0].text_content().strip()
                    if div_name == u'제작진' and key == u'각본':
                        tmps = tag.xpath('.//dd/a')
                        for tmp in tmps:
                            entity.credits.append(tmp.text_content().strip())
                    elif div_name == u'영화사' and key == u'제작':
                        tmps = tag.xpath('.//dd/a')
                        for tmp in tmps:
                            entity.producers.append(tmp.text_content().strip())
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    """




    @classmethod
    def info_photo(cls, code, entity):
        try:
            #url = "https://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s" % code[2:]
            url = "https://movie.daum.net/api/movie/%s/photoList?page=1&size=100" % code[2:]
            data = requests.get(url).json()['contents']
            #logger.debug(json.dumps(data, indent=4))
            poster_count = art_count = 0
            max_poster_count = 5
            max_art_count = 5
            for item in data:
                art = EntityThumb()
                if poster_count < max_poster_count and item['movieCategory'].find(u'포스터') != -1:
                    if item['movieCategory'] == u'메인 포스터':
                        score = 65
                    elif item['movieCategory'] == u'포스터':
                        score = 60
                    else:
                        score = 55
                    entity.art.append(EntityThumb(aspect='poster', value=item['imageUrl'], site=cls.site_name, score=score-poster_count))
                    poster_count += 1
                elif art_count < max_art_count and item['movieCategory'] == u'스틸':
                    entity.art.append(EntityThumb(aspect='landscape', value=item['imageUrl'], site=cls.site_name, score=60-art_count))
                    art_count += 1
                if poster_count == max_poster_count and art_count == max_art_count:
                    break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def info_video(cls, code, entity):
        #https://movie.daum.net/api/video/list/movie/97728?page=1&size=20
        try:
            for i in range(1, 5):
                url = 'https://movie.daum.net/api/video/list/movie/%s?page=%s&size=20' % (code[2:], i)
                data = requests.get(url).json()
                for item in data['contents']:
                    if item['adultOption'] == 'T':
                        continue
                    extra = EntityExtra2()
                    extra.content_type = 'Trailer' if item['subtitle'].find(u'예고편') != -1 else 'Featurette'
                    extra.mode = 'kakao'
                    extra.content_url = item['videoUrl'].split('/')[-1]
                    extra.title = item['title']
                    extra.thumb = item['thumbnailUrl']
                    entity.extras.append(extra)
                if data['page']['last']:
                    break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    

    """

    @classmethod
    def info_video(cls, code, entity):
        #https://movie.daum.net/api/video/list/movie/97728?page=1&size=20
        try:
            for i in range(1, 5):
                url = 'https://movie.daum.net/moviedb/videolist.json?id=%s&page=%s' % (code[2:], i)
                data = requests.get(url).json()
                for item in data['vclipList']:
                    if item['adultFlag'] == 'T':
                        continue
                    extra = EntityExtra2()
                    extra.content_type = 'Trailer' if item['vclipCategory'] == '9' else 'Featurette'
                    extra.mode = 'kakao'
                    extra.content_url = item['tvpotId']
                    extra.title = item['title']
                    extra.thumb = item['image']
                    entity.extras.append(extra)
                if data['vclipPage']['current'] == data['vclipPage']['last']:
                    break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def info_photo(cls, code, entity):
        try:
            #url = "https://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s" % code[2:]
            url = "https://movie.daum.net/api/movie/%s/photoList?page=1&size=100" % code[2:]
            data = requests.get(url).json()['data']
            #logger.debug(json.dumps(data, indent=4))
            poster_count = art_count = 0
            max_poster_count = 5
            max_art_count = 5
            for item in data:
                art = EntityThumb()
                if item['photoCategory'] == '1' and poster_count < max_poster_count:
                    entity.art.append(EntityThumb(aspect='poster', value=item['fullname'], site=cls.site_name, score=60-poster_count))
                    poster_count += 1
                elif item['photoCategory'] in ['2', '50'] and art_count < max_art_count:
                    entity.art.append(EntityThumb(aspect='landscape', value=item['fullname'], site=cls.site_name, score=60-art_count))
                    art_count += 1
                if poster_count == max_poster_count and art_count == max_art_count:
                    break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def info_cast(cls, code, entity):
        try:
            url = "https://movie.daum.net/data/movie/movie_info/cast_crew.json?movieId=%s" % code[2:]
            data = requests.get(url).json()['data']
            #logger.debug(json.dumps(data, indent=4))
            for item in data:
                name = item['nameKo'] if item['nameKo'] else item['nameEn']

                if item['castcrew']['castcrewCastName'] in [u'감독', u'연출']:
                    entity.director.append(name)
                elif item['castcrew']['castcrewCastName'] == u'제작':
                    entity.producers.append(name)
                elif item['castcrew']['castcrewCastName'] in [u'극본', u'각본']:
                    entity.credits.append(name)
                elif item['castcrew']['castcrewCastName'] in [u'주연', u'조연', u'출연', u'진행']:
                    actor = EntityActor('', site=cls.site_name)
                    actor.name = name
                    actor.originalname = item['nameEn']
                    actor.role = item['castcrew']['castcrewTitleKo']
                    if item['photo']['fullname']:
                        actor.thumb = item['photo']['fullname']
                    entity.actor.append(actor)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    
    @classmethod
    def info_basic_by_api(cls, code, entity):
        try:
            url = "https://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s" % code[2:]
            data = requests.get(url).json()['data']
            #logger.debug(json.dumps(data, indent=4))
            entity.title = data['titleKo']
            entity.extra_info['title_en'] = data['titleEn']
            entity.year = data['prodYear']
            entity.plot = re.sub(r'\<.*?\>', '', data['plot'].replace('<br>','\r\n'))
            entity.mpaa = data['admissionDesc']
            try: entity.premiered = '%s-%s-%s' % (data['releaseDate'][0:4],data['releaseDate'][4:6], data['releaseDate'][6:8])
            except: pass
            for genre in data['genres']:
                entity.genre.append(genre['genreName'])
            for genre in data['countries']:
                entity.country.append(genre['countryKo'])
            try: entity.ratings.append(EntityRatings(float(data['moviePoint']['inspectPointAvg']), name=cls.site_name))
            except: pass
            try: entity.art.append(EntityThumb(aspect='poster', value=data['photo']['fullname'], site=cls.site_name, score=70))
            except: pass
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        
    """


"""

https://movie.daum.net/api/video/list/movie/97728?page=1&size=20
https://movie.daum.net/api/movie/97728/photoList?page=1&size=100
https://movie.daum.net/api/movie/97728/dailyAttendanceList

"""




























































""" 
2021-05-30


    @classmethod
    def search_movie_web(cls, result_list, keyword, year):
        
        try:
            #movie_list = []
            url = 'https://suggest-bar.daum.net/suggest?id=movie&cate=movie&multiple=1&mod=json&code=utf_in_out&q=%s' % (py_urllib.quote(str(keyword)))
            logger.debug(url)
            data = SiteUtil.get_response(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies()).json()

            #logger.debug(json.dumps(data, indent=4))
            if 'movie' in data['items']:
                for idx, item in enumerate(data['items']['movie']):
                    if idx > 5:
                        break
                    tmps = item.split('|')
                    entity = EntitySearchItemMovie(cls.site_name)
                    entity.title = tmps[0]
                    entity.code = cls.module_char + cls.site_char + tmps[1]
                    if len(tmps) == 5:
                        entity.image_url = tmps[2]
                        entity.year = int(tmps[3])
                    else:
                        if not tmps[2].startswith('http'):
                            entity.year = int(tmps[2])

                    if SiteUtil.compare(keyword, entity.title):
                        if year != 1900:
                            if abs(entity.year-year) <= 1:
                                entity.score = 100
                            else:
                                entity.score = 80
                        else:
                            entity.score = 95
                    else:
                        entity.score = 80 - (idx*5)
                    if entity.score < 10:
                        entity.score = 10
                    cls.movie_append(result_list, entity.as_dict())
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
       

        try:
            #url = 'https://suggest-bar.daum.net/suggest?id=movie_v2&cate=movie&multiple=1&q=%s%s' % ('%EC%98%81%ED%99%94+', py_urllib.quote(str(keyword)))
            #url = 'https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=%s%s' % ('%EC%98%81%ED%99%94+', py_urllib.quote(str(keyword)))
            #logger.debug('1111111111111')
            #logger.debug(url)
            new_item, movie = cls.get_movie_info_from_home(url, keyword, year)
            if new_item is not None:
                # 부제목때문에 제목은 체크 하지 않는다.
                # 홈에 검색한게 년도도 같다면 score : 100을 주고 다른것은 검색하지 않는다.
                if new_item['year'] == year:
                    new_item['score'] = 100
                    need_another_search = False
                else:
                    new_item['score'] = 90
                    need_another_search = True

                cls.movie_append(result_list, new_item)

                logger.debug('need_another_search : %s' % need_another_search)
               
                #movie = ret['movie']
                if need_another_search:
                    # 동명영화
                    tmp = movie.find('div[@class="coll_etc"]')
                    logger.debug('coll_etc : %s' % tmp)
                    if tmp is not None:
                        first_url = None
                        tag_list = tmp.findall('.//a')

                        for idx, tag in enumerate(tag_list):
                            match = re.compile(r'(.*?)\((.*?)\)').search(tag.text_content())
                            
                            if match:
                                entity = EntitySearchItemMovie(cls.site_name)
                                entity.code = cls.module_char + cls.site_char + tag.attrib['href'].split('||')[1]
                                entity.title = match.group(1)
                                entity.year = int(match.group(2))

                                if SiteUtil.compare(keyword, entity.title):
                                    if year != 1900:
                                        if abs(entity.year-year) <= 1:
                                            entity.score = 100
                                        else:
                                            entity.score = 80
                                    else:
                                        entity.score = 95 - idx
                                else:
                                    entity.score = 80 - (idx*5)

                                cls.movie_append(result_list, entity.as_dict())

                                if entity.score == 100:
                                    first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                                
                        logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            new_ret, dummy = cls.get_movie_info_from_home(first_url, keyword, year)
                            cls.movie_append(result_list, new_ret)

                    #시리즈
                    tmp = movie.find('.//ul[@class="list_thumb list_few"]')
                    if tmp is None:
                        tmp = movie.find('.//ul[@class="list_thumb list_more"]')
                    
                    logger.debug('SERIES:%s' % tmp)
                    if tmp is not None:
                        tag_list = tmp.findall('.//div[@class="wrap_cont"]')
                        first_url = None
                        score = 80
                        for tag in tag_list:
                            a_tag = tag.find('a')
                            daum_id = a_tag.attrib['href'].split('||')[1]
                            daum_name = a_tag.text_content()
                            span_tag = tag.find('span')
                            tmp_year = span_tag.text_content()
                            logger.debug('daum_id:%s %s %s' % (daum_id, tmp_year, daum_name))
                            if daum_name == keyword and str(year) == tmp_year:
                                first_url = 'https://search.daum.net/search?%s' % a_tag.attrib['href']
                            elif str(year) == tmp_year and first_url is not None:
                                first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                            
                            #MovieSearch.movie_append(movie_list, {'id':daum_id, 'title':daum_name, 'year':year, 'score':score}) 
                            entity = EntitySearchItemMovie(cls.site_name)
                            entity.code = cls.module_char + cls.site_char + daum_id
                            entity.title = daum_name
                            entity.year = int(tmp_year)
                            entity.score = score
                            cls.movie_append(result_list, entity.as_dict()) 
                            logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            #logger.debug('RRRRRRRRRRRRRRRRRRRRRR')
                            new_ret, dummy = cls.get_movie_info_from_home(first_url, keyword, year)
                            cls.movie_append(result_list, new_ret)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        result_list = list(reversed(sorted(result_list, key=lambda k:k['score'])))
        return result_list


    @classmethod
    def get_movie_info_from_home(cls, url, keyword, year):
        try:
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            movie = None
            try:
                movie = root.get_element_by_id('movieEColl')
            except Exception as e: 
                pass
            if movie is None:
                return None, None
            
            new_item = EntitySearchItemMovie(cls.site_name)
            new_item.title = movie.xpath('.//*[@id="movieTitle"]/a/b')[0].text_content()
            new_item.code = cls.module_char + cls.site_char + movie.xpath('.//*[@id="movieTitle"]/a')[0].attrib['href'].split('=')[1]    
            new_item.image_url = movie.xpath('//*[@id="nmovie_img_0"]/a/img')[0].attrib['src']

            tmp = movie.xpath('.//*[@id="movieTitle"]/span')[0].text_content()
            match = re.compile(r'(?P<year>\d{4})\s%s' % u'제작').search(tmp)
            if match:
                new_item.year = int(match.group('year'))
                new_item.extra_info['title_en'] = tmp.split(',')[0].strip()
            
            idx = 0
            if SiteUtil.compare(keyword, new_item.title) or ('title_en' in new_item.extra_info and SiteUtil.compare(keyword, new_item.extra_info['title_en'])):
                if year != 1900:
                    if abs(new_item.year-year) <= 1:
                        new_item.score = 100
                    else:
                        new_item.score = 80
                else:
                    new_item.score = 95
            else:
                new_item.score = 80 - (idx*5)

            return new_item.as_dict(), movie
            #return {'movie':movie, 'title':title, 'daum_id':daum_id, 'year':tmp_year, 'country':country, 'more':more}

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def movie_append(cls, result_list, new_item):
        try:
            flag_exist = False
            for item in result_list:
                if item['code'] == new_item['code']:
                    flag_exist = True
                    item['score'] = new_item['score']
                    item['title'] = new_item['title']
                    item['year'] = new_item['year']
                    item['image_url'] = new_item['image_url']
                    break
            if not flag_exist:
                result_list.append(new_item)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())














"""
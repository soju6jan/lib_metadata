
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
            result_list = []
            cls.search_movie_web(result_list, keyword, year)

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
    def search_movie_web(cls, result_list, keyword, year):
        
        try:
            #movie_list = []
            url = 'https://suggest-bar.daum.net/suggest?id=movie&cate=movie&multiple=1&mod=json&code=utf_in_out&q=%s' % (py_urllib.quote(str(keyword)))
            data = SiteUtil.get_response(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies()).json()

            #logger.debug(json.dumps(data, indent=4))
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
            url = 'https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=%s%s' % ('%EC%98%81%ED%99%94+', py_urllib.quote(str(keyword)))
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
                return None
            
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
    def info(cls, code):
        try:
            ret = {}
            entity = EntityMovie2(cls.site_name, code)
            entity.code_list.append(['daum_id', code[2:]])
            cls.info_basic_by_api(code, entity)
            cls.info_cast(code, entity)
            cls.info_photo(code, entity)
            cls.info_video(code, entity)



            """
            url = 'https://movie.daum.net/moviedb/main?movieId=%s' % metadata_id
            data = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            tags = root.xpath('//span[@class="txt_name"]')
            tmp = tags[0].text_content().split('(')
            metadata.title = urllib.unquote(tmp[0])

            
            data = JSON.ObjectFromURL(url=DAUM_MOVIE_CAST % metadata_id)
            data = JSON.ObjectFromURL(url=DAUM_MOVIE_PHOTO % metadata_id)
            DAUM_MOVIE_SRCH   = "http://movie.daum.net/data/movie/search/v2/%s.json?size=20&start=1&searchText=%s"

            DAUM_MOVIE_DETAIL = "http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s"


            DAUM_MOVIE_CAST   = "http://movie.daum.net/data/movie/movie_info/cast_crew.json?pageNo=1&pageSize=100&movieId=%s"
            DAUM_MOVIE_PHOTO  = "http://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s"
            """


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
    def info_video(cls, code, entity):
        try:
            for i in range(1, 5):
                url = 'https://movie.daum.net/moviedb/videolist.json?id=%s&page=%s' % (code[2:], i)
                data = requests.get(url).json()
                for item in data['vclipList']:
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
            url = "https://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s" % code[2:]
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

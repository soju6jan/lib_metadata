
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
            
            movie_list = MovieSearch.search_movie_web(movie_list, movie_name, year)
            if movie_list and movie_list[0]['score'] == 100:
                logger.debug('SEARCH_MOVIE STEP 1 : %s' % movie_list)
                return is_include_kor, movie_list

            if kor is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, kor, year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 2 : %s' % movie_list)
                    return is_include_kor, movie_list

            if eng is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, eng, year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 3 : %s' % movie_list)
                    return is_include_kor, movie_list

            #검찰측의 죄인 検察側の罪人. Kensatsu gawa no zainin. 2018.1080p.KOR.FHDRip.H264.AAC-RTM
            # 영어로 끝나지전은 한글
            # 그 한글중 한글로 시작하지 않는곳까지
            if kor is not None:
                tmps = kor.split(' ')
                index = -1
                for i in range(len(tmps)):
                    if ord(u'가') <= ord(tmps[i][0]) <= ord(u'힣') or ord('0') <= ord(tmps[i][0]) <= ord('9'):
                        pass
                    else:
                        index = i
                        break
                if index != -1:
                    movie_list = MovieSearch.search_movie_web(movie_list, ' '.join(tmps[:index]), year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 4 : %s' % movie_list)
                        return is_include_kor, movie_list

            if is_plex == False:
                # 95점이면 맞다고 하자. 한글로 보내야하기때문에 검색된 이름을..
                if movie_list and movie_list[0]['score'] == 95:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie_list[0]['title'], year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 5 : %s' % movie_list)
                        return is_include_kor, movie_list

            # IMDB
            if is_include_kor == False:
                movie = MovieSearch.search_imdb(movie_name.lower(), year)
                if movie is not None:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie['title'], year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP IMDB : %s' % movie_list)
                        return is_include_kor, movie_list

            logger.debug('SEARCH_MOVIE STEP LAST : %s' % movie_list)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret



    @classmethod
    def search_movie_web(cls, result_list, keyword, year):
        """
        try:
            #movie_list = []
            url = 'https://suggest-bar.daum.net/suggest?id=movie&cate=movie&multiple=1&mod=json&code=utf_in_out&q=%s' % (py_urllib.quote(str(keyword)))
            data = SiteUtil.get_response(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies()).json()


            for idx, item in enumerate(data['items']['movie']):
                if idx > 5:
                    break
                tmps = item.split('|')
                entity = EntitySearchItemMovie(cls.site_name)
                entity.title = tmps[0]
                entity.code = cls.module_char + cls.site_char + tmps[1]
                entity.image_url = tmps[2]
                entity.year = int(tmps[3])

                if SiteUtil.compare(keyword, entity.title):
                    if year != 1900:
                        if year == entity.year:
                            entity.score = 100
                        elif abs(entity.year-year) == 1:
                            entity.score = 95 - idx
                        else:
                            entity.score = 80 - idx
                    else:
                        entity.score = 95 - idx
                else:
                    entity.score = 80 - (idx*5)
                if entity.score < 10:
                    entity.score = 10
                cls.movie_append(result_list, entity.as_dict())
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        """
        


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
                                        if year == entity.year:
                                            entity.score = 100
                                        elif abs(entity.year-year) == 1:
                                            entity.score = 95 - idx
                                        else:
                                            entity.score = 80 - idx
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
            if SiteUtil.compare(keyword, new_item.title):
                if year != 1900:
                    if year == new_item.year:
                        new_item.score = 100
                    elif abs(new_item.year-year) == 1:
                        new_item.score = 95 - idx
                    else:
                        new_item.score = 80 - idx
                else:
                    new_item.score = 95 - idx
            else:
                new_item.score = 80 - (idx*5)

            logger.debug('11111111111111111111')
            logger.debug(new_item.title)
            return new_item.as_dict(), movie
            #return {'movie':movie, 'title':title, 'daum_id':daum_id, 'year':tmp_year, 'country':country, 'more':more}

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
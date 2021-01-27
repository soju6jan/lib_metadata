
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
            ret['basic'] = cls.info_basic(code, None, api_return=True)
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
                try: entity.desc = item['nations'][0]['name']
                except: pass

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
                result_list.append(entity.as_dict())

            if result_list:
                ret['ret'] = 'success'
                ret['data'] = result_list
            else:
                ret['ret'] = 'empty'
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
    def info_basic(cls, code, entity, api_return=False):
        try:
            url = 'https://api-mars.watcha.com/api/contents/%s.json' % code
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
                tmp = item['text'].replace('\n', '\r\n')
                #logger.debug(tmp)
                tmp = re.sub(r'[^ %s-=+,#/\?:^$.@*\"~&%%!\\|\(\)\[\]\<\>`\'A-Za-z]' % u'ㄱ-ㅣ가-힣', '', tmp)
                #logger.debug(tmp)
                review.text += ']   ' + tmp
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





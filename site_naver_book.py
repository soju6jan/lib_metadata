
# -*- coding: utf-8 -*-


import requests, re, json, time, sys
import traceback, unicodedata
from datetime import datetime

from lxml import html, etree
import xmltodict

from framework import SystemModelSetting, py_urllib, py_urllib2
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite


from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemMovie, EntityMovie2, EntityExtra2
from tool_base import d
from .site_util import SiteUtil
from .site_naver import SiteNaver

logger = P.logger



class SiteNaverBook(SiteNaver):
    @classmethod
    def search_api(cls, titl, auth, cont, isbn, publ):
        logger.debug(f"책 검색 : [{titl}] [{auth}] ")
        trans_papago_key = SystemModelSetting.get_list('trans_papago_key')
        for tmp in trans_papago_key:
            client_id, client_secret = tmp.split(',')
            try:
                if client_id == '' or client_id is None or client_secret == '' or client_secret is None: 
                    return text
                #url = "https://openapi.naver.com/v1/search/book.json?query=%s&display=100" % py_urllib.quote(str(keyword))
                url = f"https://openapi.naver.com/v1/search/book_adv.xml?display=100"
                if titl != '':
                    url += f"&d_titl={py_urllib.quote(str(titl))}"
                if auth != '':
                    url += f"&d_auth={py_urllib.quote(str(auth))}"
                if cont != '':
                    url += f"&d_cont={py_urllib.quote(str(cont))}"
                if isbn != '':
                    url += f"&d_isbn={py_urllib.quote(str(isbn))}"
                if publ != '':
                    url += f"&d_publ={py_urllib.quote(str(publ))}"
                
                requesturl = py_urllib2.Request(url)
                requesturl.add_header("X-Naver-Client-Id", client_id)
                requesturl.add_header("X-Naver-Client-Secret", client_secret)
                #response = py_urllib2.urlopen(requesturl, data = data.encode("utf-8"))
                response = py_urllib2.urlopen(requesturl)
                data = response.read()
                data = json.loads(json.dumps(xmltodict.parse(data)))
                #logger.warning(data)
                rescode = response.getcode()
                if rescode == 200:
                    return data
                else:
                    continue
            except Exception as exception:
                logger.error('Exception:%s', exception)
                logger.error(traceback.format_exc())

    @classmethod
    def search(cls, titl, auth, cont, isbn, publ):
        data = cls.search_api(titl, auth, cont, isbn, publ)
        #logger.warning(d(data))
        result_list = []
        ret = {}

        if data['rss']['channel']['total'] != '0':
            tmp = data['rss']['channel']['item'] 
            if type(tmp) == type({}):
                tmp = [tmp]
            for idx, item in enumerate(tmp):
                #logger.debug(d(item))
                
                entity = {}
                entity['code'] = 'BN' + item['link'].split('bid=')[1]
                entity['title'] = item['title'].replace('<b>', '').replace('</b>', '')
                entity['image'] = item['image']
                try:
                    entity['author'] = item['author'].replace('<b>', '').replace('</b>', '')
                except:
                    entity['author'] = ''
                entity['publisher'] = item['publisher']
                entity['description'] = ''
                try:
                    if item['description'] is not None:
                        entity['description'] = item['description'].replace('<b>', '').replace('</b>', '')
                except:
                    pass
                #logger.warning(idx)
                if titl in entity['title'] and auth in entity['author']:
                    if entity['image'] != None:
                        entity['score'] = 100 - idx
                    else:
                        entity['score'] = 90 - idx
                elif titl in entity['title']:
                    entity['score'] = 95 - idx*5
                else:
                    entity['score'] = 90 - idx*5
                if entity['description'] == '':
                    entity['score'] += -10
                #logger.error(entity['score'])
                result_list.append(entity)
        else:
            logger.warning("검색 실패")
        if result_list:
            ret['ret'] = 'success'
            ret['data'] = result_list
        else:
            ret['ret'] = 'empty'
        return ret

    
    @classmethod
    def change_for_plex(cls, text):
        return text.replace('<p>', '').replace('</p>', '').replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&apos;', '‘').replace('&quot;', '"').replace('&#13;', '').replace('<b>', '').replace('</b>', '')


    @classmethod
    def info(cls, code):
        url = 'http://book.naver.com/bookdb/book_detail.php?bid=' + code[2:].rstrip('A')
        logger.warning(url)
        entity = {}
        root = SiteUtil.get_tree(url, headers=cls.default_headers)
        entity['code'] = code
        entity['title'] = cls.change_for_plex(root.xpath('//div[@class="book_info"]/h2/a/text()')[0].strip())
        entity['poster'] = root.xpath('//div[@class="book_info"]/div[1]/div/a/img')[0].attrib['src'].split('?')[0]
        entity['ratings'] = root.xpath('//*[@id="txt_desc_point"]/strong[1]/text()')[0]
        tmp = root.xpath('//div[@class="book_info"]/div[2]/div[2]')[0].text_content().strip()
        tmps = tmp.split('|')
        #logger.warning(tmps)
        #if len(tmps) == 3:
        #entity['author'] = tmps[0].replace('저자', '').strip()
        try:
            entity['author'] = tmps[0].replace('저자', '').replace('글', '').strip()
            entity['publisher'] = tmps[-2].strip()
            entity['premiered'] = tmps[-1].replace('.', '')
        except:
            pass

        try:
            tmp = etree.tostring(root.xpath('//*[@id="bookIntroContent"]/p')[0], pretty_print=True, encoding='utf8').decode('utf8')
            entity['desc'] = cls.change_for_plex(tmp)
        except:
            entity['desc'] = ''

        try:
            tmp = etree.tostring(root.xpath('//*[@id="authorIntroContent"]/p')[0], pretty_print=True, encoding='utf8').decode('utf8')
            entity['author_intro'] = cls.change_for_plex(tmp)
        except:
            entity['author_intro'] = ''
        
        return entity

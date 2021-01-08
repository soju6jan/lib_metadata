
# -*- coding: utf-8 -*-
import requests, re, json
import traceback

from lxml import html

from framework import SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite


from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow
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
            entity = EntitySearchItemTv(cls.site_name)

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

            entity.image_url = 'https:' + root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src']


            logger.debug('get_show_info_on_home status: %s', entity.status)
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div')
            entity.extra_info = SiteUtil.change_html(tags[0].text_content().strip())

            logger.debug('get_show_info_on_home extra_info: %s', entity.extra_info)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/a')
            if len(tags) == 1:
                entity.studio = tags[0].text
            else:
                tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span[1]')
                if len(tags) == 1:
                    entity.studio = tags[0].text
            logger.debug('get_show_info_on_home studio: %s', entity.studio)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span')
            extra_infos = [tag.text for tag in tags]
            entity.broadcast_info = extra_infos[-2].strip()
            entity.broadcast_term = extra_infos[-1].split(',')[-1].strip()
            entity.year = re.compile(r'(?P<year>\d{4})').search(extra_infos[-1]).group('year')
            
            entity.desc = root.xpath('//*[@id="tv_program"]/div[1]/dl[1]/dd/text()')[0]
            

            #logger.debug('get_show_info_on_home 1: %s', entity['status'])
            #시리즈
            entity.series = []
            entity.series.append({'title':entity.title, 'code' : entity.code, 'year' : entity.year})
            tags = root.xpath('//*[@id="tv_series"]/div/ul/li')

            if tags:
                # 2019-03-05 시리즈 더보기 존재시
                try:
                    more = root.xpath('//*[@id="tv_series"]/div/div/a')
                    url = more[0].attrib['href']
                    if not url.startswith('http'):
                        url = 'https://search.daum.net/search%s' % url
                    logger.debug('MORE URL : %s', url)
                    if more[0].xpath('span')[0].text == u'시리즈 더보기':
                        #more_root = HTML.ElementFromURL(url)
                        more_root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
                        tags = more_root.xpath('//*[@id="series"]/ul/li')
                except Exception as exception:
                    logger.debug('Not More!')
                    logger.debug(traceback.format_exc())

                for tag in tags:
                    dic = {}
                    dic['title'] = tag.xpath('a')[0].text
                    dic['code'] = cls.module_char + cls.site_char + re.compile(r'irk\=(?P<id>\d+)').search(tag.xpath('a')[0].attrib['href']).group('id')
                    if tag.xpath('span'):
                        dic['date'] = tag.xpath('span')[0].text
                        dic['year'] = re.compile(r'(?P<year>\d{4})').search(dic['date']).group('year')
                    else:
                        dic['year'] = None
                    entity.series.append(dic)
                entity.series = sorted(entity.series, key=lambda k: int(k['code'][2:])) 
            logger.debug('SERIES : %s', len(entity.series))
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
                            entity['equal_name'].append(dic)
                        elif tag.text == u'(동명회차)':
                            continue
            logger.debug(entity)
            return entity.as_dict()
        except Exception as exception:
            logger.debug('Exception get_show_info_by_html : %s', exception)
            logger.debug(traceback.format_exc())



class SiteDaumTv(SiteDaum):
    
    site_base_url = 'https://search.daum.net'
    module_char = 'K'
    site_char = 'D'

    

    @classmethod 
    def search(cls, keyword, daum_id=None, year=None, image_mode='0'):
        try:
            ret = {}
            if daum_id is None:
                url = 'https://search.daum.net/search?q=%s' % (py_urllib.quote(keyword.encode('utf8')))
            else:
                url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(keyword.encode('utf8')), daum_id)

            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            data = cls.get_show_info_on_home(root)
            #logger.debug(data)
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
            ret = {}
            show = EntityShow(cls.site_name, code)

            url = 'https://search.daum.net/search?w=tv&q=%s&irk=%s&irt=tv-program&DA=TVP' % (title, code[2:])
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            

            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/strong')
            if len(tags) == 1:
                show.title = tags[0].text_content().strip()

            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[3]/span')
            logger.debug('11111')
            logger.debug(tags)
            if tags:
                show.studio = tags[0].text_content().strip()
                summary = ''    
                for tag in tags:
                    entity.plot += tag.text.strip()
                    entity.plot += ' '
                match = re.compile(r'(\d{4}\.\d{1,2}\.\d{1,2})~').search(entity.plot)
                if match:
                    show.premiered = match.group(1)



            ret['ret'] = 'success'
            ret['data'] = show.as_dict()



        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret


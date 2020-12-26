
# -*- coding: utf-8 -*-
import os, traceback

import requests
from lxml import html

from framework import SystemModelSetting, py_urllib
from system import SystemLogicTrans

from .plugin import P
from .site_util import SiteUtil

logger = P.logger

# 사이트 차단

class SiteAvdbs(object):
    @staticmethod
    def get_actor_info(entity_actor, proxy_url=None, retry=True):
        try:
            url = 'https://www.avdbs.com/w2017/page/search/search_actor.php?kwd=%s' % entity_actor['originalname']
            proxies = None
            if proxy_url is not None:
                proxies = {"http"  : proxy_url, "https" : proxy_url}
            res = requests.get(url, headers=SiteUtil.default_headers, proxies=proxies)
            #logger.debug('avdbs status code : %s', res.status_code)
            #logger.debug(res.text)
            res.encoding = 'utf-8'
            data = '<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">' + res.text
            tree = html.fromstring(data)
            nodes = tree.xpath('//img')
            if nodes:
                entity_actor['thumb'] = SiteUtil.process_image_mode('3', nodes[0].attrib['src'].strip())
                nodes = tree.xpath('//div[@class="dscr"]/p')
                entity_actor['name'] = nodes[0].xpath('./a')[0].text_content().strip()
                entity_actor['name2'] = nodes[1].xpath('./a')[0].text_content().strip().split('(')[0]
                entity_actor['site'] = 'avdbs'
            else:
                logger.debug('mmmmmmmmmmmmm')
            return entity_actor
        except ValueError:
            # 2020-06-01
            # 단시간에 많은 요청시시 Error발생
            if retry:
                logger.debug(u'단시간 많은 요청으로 재요청')
                time.sleep(2)
                return SiteAvdbs.get_actor_info(entity_actor, proxy_url=proxy_url, retry=False)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return entity_actor

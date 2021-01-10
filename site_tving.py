
# -*- coding: utf-8 -*-
import os, requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html


from framework import app, SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite

from lib_metadata import MetadataServerUtil

from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow
from .site_util import SiteUtil
logger = P.logger


class SiteTving(object):
    site_name = 'tmdb'



class SiteTvingTv(SiteTving):
    module_char = 'K'
    site_char = 'V'


    @classmethod 
    def search_tv_by_episode_code(cls, episode_code):
        try:
            logger.debug('search_tv_by_episode_code : %s', episode_code)
            import  framework.tving.api as Tving
            data, video_url = Tving.get_episode_json_default(episode_code, 'stream50')

            
            logger.debug(data['body']['content']['info']['program'])
            logger.debug(video_url)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return


#https://search.tving.com/search/common/module/getAkc.jsp?kwd=SKY+%EC%BA%90%EC%8A%AC

# CAIP0200, CAIP0400, CAIP0500 : 동일 1280*720 0.5625
# CAIP0900 : 480*693 1.4437
# CAIP1500 : 1280*720
# CAIP1500 : 757*137 배너
# CAIP1900 : 1248*280 배너
# CAIP2000 : 152*152
# CAIP2100 : 1000*692
# CAIP2200 : 1600*795
# CAIP2300 : 663*960
# CAIP2400 : 663*960 - 1.4479

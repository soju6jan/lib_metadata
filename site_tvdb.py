
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
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings,  EntitySearchItemMovie, EntityMovie2, EntityExtra2
from .site_util import SiteUtil
logger = P.logger

try:
    import tvdb_api
except:
    os.system("{} install tvdb-api".format(app.config['config']['pip']))
    import tvdb_api
tvdb = tvdb_api.Tvdb(apikey='D4DDDAEFAD083E6F') 


class SiteTvdb(object):
    site_name = 'tvdb'



class SiteTvdbTv(SiteTvdb):
    module_char = 'K'
    site_char = 'U'

    @classmethod 
    def search(cls, keyword):
        try:
            ret = {}
            data = tvdb.search('prison break')

            ret['ret'] = 'success'
            ret['data'] = data
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret
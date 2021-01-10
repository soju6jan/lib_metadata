
# -*- coding: utf-8 -*-
import os, requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html


from framework import app, SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite

import  framework.wavve.api as Wavve
from lib_metadata import MetadataServerUtil

from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow
from .site_util import SiteUtil
logger = P.logger


class SiteWavve(object):
    site_name = 'tving'



class SiteWavveTv(SiteWavve):
    module_char = 'K'
    site_char = 'W'


    @classmethod 
    def search(cls, keyword):
        try:
            data = Wavve.search(keyword)
            return data
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return



# -*- coding: utf-8 -*-
import os, requests, re, json, time
import traceback, unicodedata
from datetime import datetime

from lxml import html


from framework import app, SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite

import  framework.tving.api as Tving
from lib_metadata import MetadataServerUtil

from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow
from .site_util import SiteUtil
logger = P.logger


class SiteTving(object):
    site_name = 'tving'



class SiteTvingTv(SiteTving):
    module_char = 'K'
    site_char = 'V'


    @classmethod 
    def apply_tv_by_episode_code(cls, show, episode_code, apply_plot=True, apply_image=True):
        try:
            #http://api.tving.com/v2/media/stream/info?info=y&screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610&noCache=1610252535&mediaCode=E001924532&streamCode=stream50&callingFrom=FLASH
            logger.debug('search_tv_by_episode_code : %s', episode_code)
            
            data, video_url = Tving.get_episode_json_default(episode_code, 'stream50')
            tving_program = data['body']['content']['info']['program']
            cls._apply_tv_by_program(show, tving_program, apply_plot=apply_plot, apply_image=apply_image)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return

    @classmethod
    def _apply_tv_by_program(cls, show, program_info, apply_plot=True, apply_image=True):
        try:
            show['extra_info']['tving_id'] = program_info['code']
            if apply_plot:
                show['plot'] = program_info['synopsis']['ko']
            if apply_image:
                tving_base = 'https://image.tving.com'
                score = 80
                for idx, img in enumerate(program_info['image']):
                    tmp_score = score - idx
                    if img['code'] in ['CAIP0200', 'CAIP1500', 'CAIP2100', 'CAIP2200']: # land
                        show['thumb'].append(EntityThumb(aspect='landscape', value=tving_base + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP0900', 'CAIP2300', 'CAIP2400']: #poster
                        show['thumb'].append(EntityThumb(aspect='poster', value=tving_base + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP1800', 'CAIP1900']: #banner
                        if img['code'] == 'CAIP1900':
                            tmp_score += 10
                        show['thumb'].append(EntityThumb(aspect='banner', value=tving_base + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP2000']: #square
                        show['thumb'].append(EntityThumb(aspect='square', value=tving_base + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @classmethod 
    def apply_tv_by_search(cls, show, apply_plot=True, apply_image=True):
        try:
            data = Tving.search_tv(show['title'])
            if data:
                for item in data:
                    if item['mast_nm'].replace(' ', '').lower() == show['title'].replace(' ', '').lower() and item['ch_nm'].replace(' ', '').lower() == show['studio'].replace(' ', '').lower():
                        # 시작일로 체크
                        tving_program = Tving.get_program_programid(item['mast_cd'])['body']
                        logger.debug(tving_program)
                        logger.debug(show['premiered'])
                        logger.debug(tving_program['broad_dt'])
                        logger.debug(show['premiered'])
                        
                        
                        #if tving_program['broad_dt'] == show['premiered'].replace('-', ''):
                        #    logger.debug(',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,')
                        cls._apply_tv_by_program(show, tving_program, apply_plot=apply_plot, apply_image=apply_image)
                        break
                        
                        #if show['premiered'] == ''
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    
#https://search.tving.com/search/common/module/getAkc.jsp?kwd=SKY+%EC%BA%90%EC%8A%AC

# CAIP0200, CAIP0400, CAIP0500 : 동일 1280*720 0.5625   landscape
# CAIP0900 : 480*693 1.4437  poster
# CAIP1500 : 1280*720    landscape
# CAIP1800 : 757*137 배너
# CAIP1900 : 1248*280 배너  
# CAIP2000 : 152*152    square
# CAIP2100 : 1000*692   landscape
# CAIP2200 : 1600*795   landscape
# CAIP2300 : 663*960   poster
# CAIP2400 : 663*960 - 1.4479   poster

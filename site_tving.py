
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


tv_mpaa_map = {'CPTG0100' : u'모든 연령 시청가', 'CPTG0200' : u'7세 이상 시청가', 'CPTG0300' : u'12세 이상 시청가', 'CPTG0400' : u'15세 이상 시청가', 'CPTG0500' : u'19세 이상 시청가'}

channel_code_map = {
    'C00551' : 'tvN',
    'C00579' : 'Mnet',
    'C00590' : 'OGN',
    'C15152' : 'CH.DIA',
    'C01582' : 'JTBC',
    'C07381' : 'OCN',
    'C06941' : 'tooniverse',

}


class SiteTving(object):
    site_name = 'tving'
    tving_base_image = 'https://image.tving.com'

    @classmethod
    def change_to_premiered(cls, broadcast_date):
        tmp = str(broadcast_date)
        return tmp[0:4] + '-' + tmp[4:6] + '-' + tmp[6:8]

    @classmethod
    def change_channel_code(cls, channel_code):
        if channel_code in channel_code_map:
            return channel_code_map[channel_code]
        return channel_code


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
            #logger.debug(show['extra_info'])
            #logger.debug(program_info['code'])
            show['extra_info']['tving_id'] = program_info['code']
            show['mpaa'] = tv_mpaa_map[program_info['grade_code']]

            if apply_plot:
                show['plot'] = program_info['synopsis']['ko']
                show['plot'] = show['plot'].replace(u'[이용권 전용 VOD] 티빙 이용권 전용 프로그램입니다.\r\n모든 방송과 4천여편의 영화를 티빙 이용권으로 즐겨보세요!\r\n\r\n', '').strip()
            
            if apply_image:
                score = 80
                for idx, img in enumerate(program_info['image']):
                    tmp_score = score - idx
                    if img['code'] in ['CAIP0200', 'CAIP1500', 'CAIP2100', 'CAIP2200']: # land
                        show['thumb'].append(EntityThumb(aspect='landscape', value=cls.tving_base_image + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP0900', 'CAIP2300', 'CAIP2400']: #poster
                        show['thumb'].append(EntityThumb(aspect='poster', value=cls.tving_base_image + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP1800', 'CAIP1900']: #banner
                        if img['code'] == 'CAIP1900':
                            tmp_score += 10
                        show['thumb'].append(EntityThumb(aspect='banner', value=cls.tving_base_image + img['url'], site=cls.site_name, score=tmp_score).as_dict())   
                    elif img['code'] in ['CAIP2000']: #square
                        show['thumb'].append(EntityThumb(aspect='square', value=cls.tving_base_image + img['url'], site=cls.site_name, score=tmp_score).as_dict())
            if True:
                import framework.tving.api as Tving
                page = 1
                while True:
                    episode_data = Tving.get_frequency_programid(program_info['code'], page=page)
                    for epi_all in episode_data['body']['result']:
                        epi = epi_all['episode']
                        if epi['frequency'] not in show['extra_info']['episodes']:
                            show['extra_info']['episodes'][int(epi['frequency'])] = {}

                        show['extra_info']['episodes'][int(epi['frequency'])][cls.site_name] = {
                            'code' : cls.module_char + cls.site_char + epi['code'],
                            'thumb' : cls.tving_base_image + epi['image'][0]['url'],
                            'plot' : epi['synopsis']['ko'],
                            'premiered' : cls.change_to_premiered(epi['broadcast_date']), 
                            'title' : '',
                        }
                    page += 1
                    if episode_data['body']['has_more'] == 'N' or page == 10:
                        break
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @classmethod 
    def apply_tv_by_search(cls, show, apply_plot=True, apply_image=True):
        try:
            data = Tving.search_tv(show['title'])
            if data:
                for item in data:
                    if item['ch_nm'].replace(' ', '').lower() == show['studio'].replace(' ', '').lower() and (item['mast_nm'].replace(' ', '').lower() == show['title'].replace(' ', '').lower() or item['mast_nm'].replace(' ', '').lower().find(show['title'].replace(' ', '').lower()) != -1 or show['title'].replace(' ', '').lower().find(item['mast_nm'].replace(' ', '').lower()) != -1):
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


    @classmethod 
    def search(cls, keyword, **kwargs):
        try:
            ret = {}
            search_list = Tving.search_tv(keyword)
            if search_list:
                show_list = []
                for idx, item in enumerate(search_list):
                    entity = EntitySearchItemTv(cls.site_name)
                    entity.code = (kwargs['module_char'] if 'module_char' in kwargs else cls.module_char) + cls.site_char + item['mast_cd']
                    entity.title = item['mast_nm']
                    entity.image_url = cls.tving_base_image + item['web_url']
                    entity.studio = item['ch_nm']
                    entity.genre = item['cate_nm']
                    if SiteUtil.compare_show_title(entity.title, keyword):
                        entity.score = 100
                    else:
                        entity.score = 60 - idx * 5

                    show_list.append(entity.as_dict())
                ret['ret'] = 'success'
                ret['data'] = show_list
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
            ret = {}
            tving_program = Tving.get_program_programid(code[2:])['body']
            #ogger.debug(tving_program)
            
            show = EntityShow(cls.site_name, code)
            show.title = tving_program['name']['ko']
            show.originaltitle = show.title
            show.sorttitle = show.title 
            show.studio = cls.change_channel_code(tving_program['channel_code'])
            show.plot = tving_program['synopsis']['ko']
            show.premiered = cls.change_to_premiered(tving_program['broad_dt'])
            try: show.year = int(show.premiered.split('-')[0])
            except: show.year = 1900
            if tving_program['broad_state'] == 'CPBS0200':
                show.status = 1
            elif tving_program['broad_state'] == 'CPBS0300':
                show.status = 2
            else:
                logger.debug('!!!!!!!!!!!!!!!!broad_statebroad_statebroad_statebroad_statebroad_statebroad_statebroad_statebroad_state')

            #if tving_program['broad_end_dt'] != '':
            #    show.status = 2
            show.genre = [tving_program['category1_name']['ko']]
            #show.episode = home_data['episode']
            
            
            for item in tving_program['actor']:
                actor = EntityActor(item)
                actor.name = item
                show.actor.append(actor)
            
            for item in tving_program['director']:
                actor = EntityActor(item)
                actor.name = item
                show.director.append(actor)

            show = show.as_dict()
            cls._apply_tv_by_program(show, tving_program)
            ret['ret'] = 'success'
            ret['data'] = show

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret
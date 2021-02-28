
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
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv, EntityShow, EntitySearchItemMovie, EntityMovie2, EntityExtra2
from .site_util import SiteUtil
logger = P.logger


tv_mpaa_map = {'CPTG0100' : u'모든 연령 시청가', 'CPTG0200' : u'7세 이상 시청가', 'CPTG0300' : u'12세 이상 시청가', 'CPTG0400' : u'15세 이상 시청가', 'CPTG0500' : u'19세 이상 시청가'}

movie_mpaa_map = {'CMMG0100': u'전체 관람가', 'CMMG0200': u'12세 관람가', 'CMMG0300': u'15세 관람가', 'CMMG0400':u'청소년 관람불가'}
channel_code_map = {
    'C00551' : 'tvN',
    'C00579' : 'Mnet',
    'C00590' : 'OGN',
    'C15152' : 'CH.DIA',
    'C01582' : 'JTBC',
    'C07381' : 'OCN',
    'C06941' : 'tooniverse',
}
product_country_map = {
    'CACT1001':u'한국', 
    'CACT4017':u'프랑스',
    'CACT4004':u'독일',
    'CACT4010':u'영국',
    'CACT4005':u'러시아',
    'CACT2002':u'미국',
    'CACT1008':u'일본',
    'CACT1012':u'홍콩',
    'CACT1009':u'중국',
    'CACT1011':u'대만',
    'CACT4025':u'아일랜드',
    'CACT1010':u'태국',
    'CACT9999':u'슬로바키아',
    'CACT4012':u'이탈리아',
    'CACT5001':u'호주',
    'CACT4009':u'스페인',
    'CACT2003':u'캐나다',
    'CACT4023':u'노르웨이',
    'CACT4018':u'핀란드',
    'CACT4006':u'벨기에',
    'CACT4013':u'체코',
    'CACT4003':u'덴마크',
    'CACT1006':u'이란',
    'CACT3002':u'브라질',
    'CACT1007':u'인도',
    'CACT4002':u'네덜란드',
    'CACT4015':u'포르투칼',
    'CACT5002':u'뉴질랜드',
    'CACT4016':u'폴란드',
    'CACT1004':u'싱가포르',
    'CACT1005':u'아프가니스탄',
    'CACT1013':u'이스라엘',
    'CACT1015':u'아랍 에미리트',
    'CACT2001':u'멕시코',
    'CACT3001':u'베네수엘라',
    'CACT3003':u'아르헨티나',
    'CACT3004':u'푸에르토리코',
    'CACT3005':u'칠레',
    'CACT4007':u'스웨덴',
    'CACT4008':u'스위스',
    'CACT4011':u'오스트리아',
    'CACT4014':u'터키',
    'CACT4019':u'헝가리',
    'CACT4020':u'불가리아',
    'CACT4027':u'아이슬란드',
    'CACT4028':u'루마니아',
    'CACT5003':u'페루',
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

    @classmethod
    def search_api(cls, keyword):
        return Tving.search(keyword)

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
            data = cls.search_api(show['title'])
            if data:
                for item in data:
                    if item['gubun'] != 'VODBC':
                        continue
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
            search_list = cls.search_api(keyword)
            if search_list:
                show_list = []
                for idx, item in enumerate(search_list):
                    if item['gubun'] == 'VODBC':
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




class SiteTvingMovie(SiteTving):
    module_char = 'M'
    site_char = 'V'

    

    @classmethod 
    def search(cls, keyword, year=1900):
        try:
            ret = {}
            search_list = cls.search_api(keyword)
            #logger.debug(json.dumps(search_list, indent=4))
            result_list = []
            if search_list:
                for idx, item in enumerate(search_list):
                    if item['gubun'] == 'VODMV':
                        entity = EntitySearchItemMovie(cls.site_name)
                        entity.code = cls.module_char + cls.site_char + item['mast_cd']
                        entity.title = item['mast_nm']
                        entity.image_url = cls.tving_base_image + item['web_url']
                        entity.desc = u'%s' % (item['cate_cd'])
                        if SiteUtil.compare(keyword, entity.title):
                            entity.score = 94
                        else:
                            entity.score = 80 - (idx*5)
                        result_list.append(entity.as_dict())
                result_list = sorted(result_list, key=lambda k: k['score'], reverse=True)  
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
            ret = {}
            
            entity = EntityMovie2(cls.site_name, code)
            entity.code_list.append(['tving_id', code[2:]])
            #wavve_data = cls.info_api(code)

            tving_data_all = Tving.get_movie_json2(code[2:])
            #logger.debug(json.dumps(tving_data_all, indent=4))
            #logger.debug(tving_data_all['body']['result']['message'])
            tving_data = tving_data_all['body']['content']['info']
   
            entity.title = tving_data['movie']['name']['ko']
            entity.extra_info['title_en'] = tving_data['movie']['name']['en']
            for item in tving_data['movie']['actor']:
                actor = EntityActor('', site=cls.site_name)
                actor.name = item
                entity.actor.append(actor)
            entity.genre.append(tving_data['movie']['category1_name']['ko'])
            entity.director = tving_data['movie']['director']
            try: entity.runtime = int(int(tving_data['duration']) / 60)
            except: pass
            try: entity.mpaa = movie_mpaa_map[tving_data['movie']['grade_code']]
            except: entity.mpaa = tving_data['movie']['grade_code']
            try: 
                entity.country.append(product_country_map[tving_data['movie']['product_country']])
            except: entity.country.append(tving_data['movie']['product_country'])
            if len(entity.country)>0 and entity.country[0] == u'한국':
                entity.originaltitle = entity.title
            else:
                entity.originaltitle = entity.extra_info['title_en']
            entity.year = tving_data['movie']['product_year']
            entity.plot = tving_data['movie']['story']['ko']
            try: entity.premiered = '%s-%s-%s' % (tving_data['movie']['release_date'][0:4],tving_data['movie']['release_date'][4:6], tving_data['movie']['release_date'][6:8])
            except: pass

            for item in tving_data['movie']['image']:
                aspect = 'landscape'
                if item['code'] in ['CAIM0400']: # land
                    pass
                elif item['code'] in ['CAIM2100']: #poster
                    aspect = 'poster'
                elif item['code'] in ['CAIM1800', 'CAIM1900']: #banner
                    aspect = 'banner'
                entity.art.append(EntityThumb(aspect=aspect, value=cls.tving_base_image + item['url'], site=cls.site_name, score=50))
            try: entity.ratings.append(EntityRatings(float(tving_data['movie']['rating']), name=cls.site_name))
            except: pass
            
            if tving_data['movie']['billing_package_tag'] == '':
                entity.extra_info['tving_stream'] = {}
                entity.extra_info['tving_stream']['drm'] = (tving_data['movie']['drm_yn'] == 'Y')
                if entity.extra_info['tving_stream']['drm'] == False:
                    entity.extra_info['tving_stream']['plex'] = '{}/metadata/api/movie/stream?apikey={}&mode=redirect&code={}'.format(SystemModelSetting.get('ddns'), SystemModelSetting.get('auth_apikey'), code)
                entity.extra_info['tving_stream']['kodi'] = 'plugin://metadata.sjva.movie/?action=play&code=%s' % code

            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()
            return ret
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret

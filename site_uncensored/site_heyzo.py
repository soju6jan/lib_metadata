# -*- coding: utf-8 -*-
import requests, re, json
import traceback
from dateutil.parser import parse

from lxml import html

from framework import SystemModelSetting
from framework.util import Util
from system import SystemLogicTrans

# lib_metadata
from ..entity_av import EntityAVSearch
from ..entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra
from ..site_util import SiteUtil

#########################################################
from ..plugin import P
logger = P.logger
ModelSetting = P.ModelSetting

class SiteHeyzo(object):
    site_name = 'heyzo'
    site_base_url = 'https://m.heyzo.com'
    module_char = 'E'
    site_char = 'H'

    @classmethod
    def search(cls, keyword, do_trans=True, proxy_url=None, image_mode='0', manual=False):
        try:
            ret = {}
            if re.search('(\\d{4})', keyword, re.I) is not None:
                keyword = re.search('(\\d{4})', keyword, re.I).group()
            else:
                ret['ret'] = 'failed'
                ret['data'] = 'invalid keyword'
                return ret

            url = f'{cls.site_base_url}/moviepages/{keyword}/index.html'

            if SiteUtil.get_response(url, proxy_url=proxy_url).status_code == 404:
                logger.debug(f'not found: {keyword}')
                ret['ret'] = 'failed'
                ret['data'] = 'not found'
                return ret

            tree = SiteUtil.get_tree(url, proxy_url=proxy_url)
            
            ret = {'data' : []}

            item = EntityAVSearch(cls.site_name)
            item.code = cls.module_char + cls.site_char + keyword

            item.title = item.title_ko = tree.xpath('//div[@id="container"]/h1/text()')[0].strip()
            item.year = parse(tree.xpath('//*[@id="moviedetail"]/div[2]/span/text()')[1].strip()).date().year

            item.image_url = f'https://m.heyzo.com/contents/3000/{keyword}/images/player_thumbnail.jpg'
            if manual == True:
                if image_mode == '3':
                    image_mode = '0'
                item.image_url = SiteUtil.process_image_mode(image_mode, item.image_url, proxy_url=proxy_url)
            
            if do_trans:
                item.title_ko = SystemLogicTrans.trans(item.title, source='ja', target='ko')
            
            item.ui_code = f'HEYZO-{keyword}'
            
            item.score = 100

            logger.debug('score :%s %s ', item.score, item.ui_code)
            ret['data'].append(item.as_dict())

            ret['data'] = sorted(ret['data'], key=lambda k: k['score'], reverse=True)  
            ret['ret'] = 'success'

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        
        return ret


    @classmethod
    def info(cls, code, do_trans=True, proxy_url=None, image_mode='0'):
        try:
            ret = {}
            url = f'{cls.site_base_url}/moviepages/{code[2:]}/index.html'
            tree = SiteUtil.get_tree(url, proxy_url=proxy_url)
            entity = EntityMovie(cls.site_name, code)
            entity.country = [u'일본']
            entity.mpaa = u'청소년 관람불가'

            # 썸네일
            entity.thumb = []
            data_poster = SiteUtil.get_image_url(f'https://m.heyzo.com/contents/3000/{code[2:]}/images/thumbnail.jpg', image_mode, proxy_url=proxy_url)
            entity.thumb.append(EntityThumb(aspect='poster', value=data_poster['image_url']))
            data_landscape = SiteUtil.get_image_url(f'https://m.heyzo.com/contents/3000/{code[2:]}/images/player_thumbnail.jpg', image_mode, proxy_url=proxy_url)
            entity.thumb.append(EntityThumb(aspect='landscape', value=data_landscape['image_url']))

            # tagline
            entity.tagline = SiteUtil.trans(tree.xpath('//div[@id="container"]/h1/text()')[0].strip(), do_trans=do_trans)

            # date, year
            entity.premiered = str(parse(tree.xpath('//*[@id="moviedetail"]/div[2]/span/text()')[1].strip()).date())
            entity.year = parse(tree.xpath('//*[@id="moviedetail"]/div[2]/span/text()')[1].strip()).date().year

            # actor
            entity.actor = []
            for actor in tree.xpath('//*[@id="moviedetail"]/div[1]/strong/text()')[0].strip().split():
                entity.actor.append(EntityActor(actor))


            # director
            # entity.director = []

            # tag
            entity.tag = []
            entity.tag.append('HEYZO')

            # genre
            entity.genre = []
            genrelist = []
            genrelist = tree.xpath('//*[@id="keyword"]/ul//li/a/text()')
            if genrelist != []:
                for item in genrelist:
                    entity.genre.append(SiteUtil.get_translated_tag('uncen_tags', item)) # 미리 번역된 태그를 포함
                    # entity.genre.append(SiteUtil.trans(item.strip(), do_trans=do_trans).strip())
            
            # title
            entity.title = entity.originaltitle = entity.sorttitle = f'HEYZO-{code[2:]}'

            # entity.ratings
            try: entity.ratings.append(EntityRatings(float(tree.xpath('//*[@id="totalRate"]/script/text()')[0].split('\'')[1], max=5, name=cls.site_name, image_url='https://m.heyzo.com/images/star.png')))
            except: pass

            # plot
            entity.plot = SiteUtil.trans(tree.xpath('//*[@id="memo"]/text()')[0], do_trans=do_trans)
            
            # 팬아트
            # entity.fanart = []

            # 제작사
            entity.studio = 'HEYZO'

            # 부가영상 or 예고편
            entity.extras = []
            entity.extras.append(EntityExtra('trailer', entity.title, 'mp4', 'https:'+re.search(r"\" src=\"(.*?)\"", tree.xpath('//*[@id="container"]/script[4]/text()')[0]).group(1), thumb=f'https://m.heyzo.com/contents/3000/{code[2:]}/images/player_thumbnail.jpg'))

            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)

        return ret

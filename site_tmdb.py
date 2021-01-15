
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

try:
    import tmdbsimple
except:
    os.system("{} install tmdbsimple".format(app.config['config']['pip']))
    import tmdbsimple
tmdbsimple.API_KEY = 'f090bb54758cabf231fb605d3e3e0468'

ARTWORK_ITEM_LIMIT = 15
POSTER_SCORE_RATIO = .3 # How much weight to give ratings vs. vote counts when picking best posters. 0 means use only ratings.
BACKDROP_SCORE_RATIO = .3
#STILLS_SCORE_RATIO = .3
#RE_IMDB_ID = Regex('^tt\d{7,10}$')

class SiteTmdb(object):
    site_name = 'tmdb'


class SiteTmdbTv(SiteTmdb):
    
    #site_base_url = 'https://search.daum.net'
    module_char = 'K'
    site_char = 'T'


    @classmethod 
    def search_tv(cls, title, premiered):
        try:
            tmdb_search = tmdbsimple.Search().tv(query=title, language='ko')
            for t in tmdb_search['results']:
                if premiered == t['first_air_date']:
                    return t['id']
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return

    @classmethod
    def process_image(cls, tmdb, show):
        try:
            tmdb_images_dict = tmdb.images()

            if tmdb_images_dict['posters']:
                max_average = max([(lambda p: p['vote_average'] or 5)(p) for p in tmdb_images_dict['posters']])
                max_count = max([(lambda p: p['vote_count'])(p) for p in tmdb_images_dict['posters']]) or 1

                for i, poster in enumerate(tmdb_images_dict['posters']):

                    score = (poster['vote_average'] / max_average) * POSTER_SCORE_RATIO
                    score += (poster['vote_count'] / max_count) * (1 - POSTER_SCORE_RATIO)
                    tmdb_images_dict['posters'][i]['score'] = score

                    # Boost the score for localized posters (according to the preference).
                    if poster['iso_639_1'] == 'ko':
                        tmdb_images_dict['posters'][i]['score'] = poster['score'] + 1

                    # Discount score for foreign posters.
                    if poster['iso_639_1'] != 'ko' and poster['iso_639_1'] is not None and poster['iso_639_1'] != 'en':
                        tmdb_images_dict['posters'][i]['score'] = poster['score'] - 1

                for i, poster in enumerate(sorted(tmdb_images_dict['posters'], key=lambda k: k['score'], reverse=True)):
                    if i > ARTWORK_ITEM_LIMIT:
                        break
                    else:
                        poster_url = 'https://www.themoviedb.org/t/p/'+ 'original' + poster['file_path']
                        thumb_url = 'https://www.themoviedb.org/t/p/' + 'w154' + poster['file_path']
                        show['thumb'].append(EntityThumb(aspect='poster', value=poster_url, thumb=thumb_url, site='tmdb', score=poster['score']).as_dict())

            if tmdb_images_dict['backdrops']:
                max_average = max([(lambda p: p['vote_average'] or 5)(p) for p in tmdb_images_dict['backdrops']])
                max_count = max([(lambda p: p['vote_count'])(p) for p in tmdb_images_dict['backdrops']]) or 1

                for i, backdrop in enumerate(tmdb_images_dict['backdrops']):
                    score = (backdrop['vote_average'] / max_average) * BACKDROP_SCORE_RATIO
                    score += (backdrop['vote_count'] / max_count) * (1 - BACKDROP_SCORE_RATIO)
                    tmdb_images_dict['backdrops'][i]['score'] = score

                    # For backdrops, we prefer "No Language" since they're intended to sit behind text.
                    if backdrop['iso_639_1'] == 'xx' or backdrop['iso_639_1'] == 'none':
                        tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) + 2

                    # Boost the score for localized art (according to the preference).
                    if backdrop['iso_639_1'] == 'ko':
                        tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) + 1

                    # Discount score for foreign art.
                    if backdrop['iso_639_1'] != 'ko' and backdrop['iso_639_1'] is not None and backdrop['iso_639_1'] != 'en':
                        tmdb_images_dict['backdrops'][i]['score'] = float(backdrop['score']) - 1

                for i, backdrop in enumerate(sorted(tmdb_images_dict['backdrops'], key=lambda k: k['score'], reverse=True)):
                    if i > ARTWORK_ITEM_LIMIT:
                        break
                    else:
                        backdrop_url = 'https://www.themoviedb.org/t/p/' + 'original' + backdrop['file_path']
                        thumb_url = 'https://www.themoviedb.org/t/p/' + 'w300' + backdrop['file_path']
                        show['thumb'].append(EntityThumb(aspect='landscape', value=backdrop_url, thumb=thumb_url, site='tmdb', score=backdrop['score']).as_dict())
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod
    def process_actor_image(cls, tmdb, show):
        try:
            tmdb_actor = tmdb.credits()
            for tmdb_item in tmdb_actor['cast']:
                if tmdb_item['profile_path'] is None:
                    continue
                kor_name = SystemLogicTrans.trans(tmdb_item['name'], source='en', target='ko').replace(' ', '')
                #kor_name = MetadataServerUtil.trans_en_to_ko(tmdb_item['name'])
                flag_find = False

                #logger.debug(tmdb_item)
                for actor in show['actor']:
                    if actor['name'] == kor_name:
                        flag_find = True
                        actor['thumb'] = 'https://www.themoviedb.org/t/p/' + 'original' + tmdb_item['profile_path']
                        break
                if flag_find == False:
                    kor_role_name = MetadataServerUtil.trans_en_to_ko(tmdb_item['character'])
                    for actor in show['actor']:
                        if actor['role'] == kor_role_name:
                            flag_find = True
                            actor['thumb'] = 'https://www.themoviedb.org/t/p/' + 'original' + tmdb_item['profile_path']
                            break
                if flag_find == False:
                    logger.debug(kor_name)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


    @classmethod 
    def apply(cls, tmdb_id, show, apply_image=True, apply_actor_image=True):
        try:
            tmdb = tmdbsimple.TV(tmdb_id)
            tmdb_dict = tmdb.info()
            
            votes = tmdb_dict['vote_count']
            rating = tmdb_dict['vote_average']

            if votes > 3:
                show['ratings'].append(EntityRatings(rating, max=10, name='tmdb').as_dict())

            if apply_image:
                cls.process_image(tmdb, show)

            if apply_actor_image:
                cls.process_actor_image(tmdb, show)
            #ret['tmdb']['info'] = tmdb.credits()
            return True
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return False





    @classmethod 
    def info(cls, code, title):
        try:
            ret = {}
            show = EntityShow(cls.site_name, code)

            # 종영와, 방송중이 표현 정보가 다르다. 종영은 studio가 없음

            url = 'https://search.daum.net/search?w=tv&q=%s&irk=%s&irt=tv-program&DA=TVP' % (title, code[2:])
            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())

            home_url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (title, code[2:])
            home_root = SiteUtil.get_tree(home_url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            home_data = cls.get_show_info_on_home(home_root)

            logger.debug('home_datahome_datahome_datahome_datahome_datahome_datahome_datahome_datahome_data')
            logger.debug(home_data)

            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/strong')
            if len(tags) == 1:
                show.title = tags[0].text_content().strip()
                show.originaltitle = show.title
                show.sorttitle = unicodedata.normalize('NFKD', show.originaltitle)
                logger.debug(show.sorttitle)
            """
            tags = root.xpath('//*[@id="tv_program"]/div[1]/div[3]/span')
            # 이 정보가 없다면 종영
            if tags:
                show.studio = tags[0].text_content().strip()
                summary = ''    
                for tag in tags:
                    entity.plot += tag.text.strip()
                    entity.plot += ' '
                match = re.compile(r'(\d{4}\.\d{1,2}\.\d{1,2})~').search(entity.plot)
                if match:
                    show.premiered = match.group(1)
            """
            show.studio = home_data['studio']
            show.plot = home_data['desc']
            match = re.compile(r'(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})~').search(home_data['broadcast_term'])
            if match:
                show.premiered = match.group('year') + '-' + match.group('month').zfill(2) + '-'+ match.group('day').zfill(2)
                show.year = int(match.group('year'))
            show.status = home_data['status']
            show.genre = [home_data['genre']]
            show.episode = home_data['episode']

            show.extra_info['daum_poster'] = cls.process_image_url(root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src'])


            """
            tags = root.xpath('//*[@id="tv_program"]/div[4]/div/ul/li')
            for tag in tags:
                a_tags = tag.xpath('.//a')
                if len(a_tags) == 2:
                    thumb = cls.process_image_url(a_tags[0].xpath('.//img')[0].attrib['src'])
                    #video_url = cls.get_kakao_play_url(a_tags[1].attrib['href'])
                    video_url = a_tags[1].attrib['href']
                    title = a_tags[1].text_content()
                    #logger.debug(video_url)
                    date = cls.change_date(tag.xpath('.//span')[0].text_content().strip())
                    show.extras.append(EntityExtra('Featurette', title, 'kakao', video_url, premiered=date, thumb=thumb))
            """


            tags = root.xpath('//*[@id="tv_program"]//div[@class="clipList"]//div[@class="mg_expander"]/a')
            if tags:
                tmp = tags[0].attrib['href']
                show.extra_info['kakao_id'] = re.compile('/(?P<id>\d+)/').search(tmp).group('id')
                logger.debug(show.extra_info['kakao_id'])


            for i in range(1,3):
                items = root.xpath('//*[@id="tv_casting"]/div[%s]/ul//li' % i)
                logger.debug('CASTING ITEM LEN : %s' % len(items))
                for item in items:
                    actor = EntityActor(None)
                    cast_img = item.xpath('div/a/img')
                    if len(cast_img) == 1:
                        actor.thumb = cls.process_image_url(cast_img[0].attrib['src'])
                    
                    span_tag = item.xpath('span')
                    for span in span_tag:
                        span_text = span.text_content().strip()
                        tmp = span.xpath('a')
                        if len(tmp) == 1:
                            role_name = tmp[0].text_content().strip()
                            tail = tmp[0].tail.strip()
                            if tail == u'역':
                                actor.type ='actor'
                                actor.role = role_name
                            else:
                                actor.name = role_name
                        else:
                            if span_text.endswith(u'역'): actor.role = span_text.replace(u'역', '')
                            elif actor.name == '': actor.name = span_text
                            else: actor.role = span_text
                    if actor.type == 'actor' or actor.role.find(u'출연') != -1:
                        show.actor.append(actor)
                    elif actor.role.find(u'감독') != -1 or actor.role.find(u'연출') != -1:
                        show.director.append(actor)
                    elif actor.role.find(u'제작') != -1 or actor.role.find(u'기획') != -1 or actor.role.find(u'책임프로듀서') != -1:
                        show.director.append(actor)
                    elif actor.role.find(u'극본') != -1 or actor.role.find(u'각본') != -1:
                        show.credits.append(actor)
                    elif actor.name != u'인물관계도':
                        show.actor.append(actor)



            ret['ret'] = 'success'
            ret['data'] = show.as_dict()



            

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret



# -*- coding: utf-8 -*-
import requests, re, json
import traceback

from lxml import html

from framework import SystemModelSetting
from framework.util import Util
from system import SystemLogicTrans

from .plugin import P
from .entity_av import EntityAVSearch
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra
from .site_util import SiteUtil

logger = P.logger



class SiteDmm(object):
    site_name = 'dmm'
    site_base_url = 'https://www.dmm.co.jp'
    module_char = 'C'
    site_char = 'D'

    dmm_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cookie' : 'age_check_done=1',
    } 

    @classmethod 
    def search(cls, keyword, do_trans=True, proxy_url=None, image_mode='0'):
        try:
            ret = {}
            keyword = keyword.strip().lower()
            # 2020-06-24
            if keyword[-3:-1] == 'cd':
                keyword = keyword[:-3]
            keyword = keyword.replace('-', ' ')
            keyword_tmps = keyword.split(' ')
            if len(keyword_tmps) == 2:
                if len(keyword_tmps[1]) <= 5:
                    dmm_keyword = '%s%s' % (keyword_tmps[0], keyword_tmps[1].zfill(5))
                elif len(keyword_tmps[1]) > 5:
                    dmm_keyword = '%s%s' % (keyword_tmps[0], keyword_tmps[1])
            else:
                dmm_keyword = keyword
            logger.debug('keyword [%s] -> [%s]', keyword, dmm_keyword)

            url = '%s/digital/videoa/-/list/search/=/?searchstr=%s' % (cls.site_base_url, dmm_keyword)
            tree = SiteUtil.get_tree(url, proxy_url=proxy_url, headers=cls.dmm_headers)
            lists = tree.xpath('//*[@id="list"]/li')
            ret = {'data' : []}
            score = 60
            logger.debug('dmm search len lists2 :%s', len(lists))
            if len(lists) > 10:
                lists = lists[:10]
            for node in lists:
                try:
                    item = EntityAVSearch(cls.site_name)
                    tag = node.xpath('.//div/p[@class="tmb"]/a')[0]
                    href = tag.attrib['href'].lower()
                    match = re.compile(r'\/cid=(?P<code>.*?)\/').search(href)
                    if match:
                        item.code = cls.module_char + cls.site_char + match.group('code')
                    already_exist = False
                    for exist_item in ret['data']:
                        if exist_item['code'] == item.code:
                            already_exist = True
                            break
                    if already_exist:
                        continue
                    
                    tag = node.xpath('.//span[1]/img')[0]
                    item.title = item.title_ko = tag.attrib['alt']
                    item.image_url = tag.attrib['src']
                    tmp = SiteUtil.discord_proxy_get_target(item.image_url)
                    if tmp is None:
                        item.image_url = SiteUtil.process_image_mode(image_mode, item.image_url, proxy_url=proxy_url)
                    else:
                        item.image_url = tmp
                    if do_trans:
                        item.title_ko = SystemLogicTrans.trans(item.title, source='ja', target='ko')
                    
                    match = re.compile(r'(h_)?\d*(?P<real>[a-zA-Z]+)(?P<no>\d+)([a-zA-Z]+)?$').search(item.code[2:])
                    if match:
                        item.ui_code = '%s%s' % (match.group('real'), match.group('no'))
                    else:
                        item.ui_code = item.code[2:]

                    if len(keyword_tmps) == 2:
                        #2019-11-20 ntr mntr 둘다100
                        if item.ui_code == dmm_keyword:
                            item.score = 100
                        elif item.ui_code.replace('0','') == dmm_keyword.replace('0',''):
                            item.score = 100
                        elif item.ui_code.find(dmm_keyword) != -1: #전체포함 DAID => AID
                            item.score = score
                            score += -5
                        elif item.code.find(keyword_tmps[0]) != -1 and item.code.find(keyword_tmps[1]) != -1:
                            item.score = score
                            score += -5
                        elif item.code.find(keyword_tmps[0]) != -1 or item.code.find(keyword_tmps[1]) != -1:
                            item.score = 60
                        else:
                            item.score = 20
                    else:
                        if item.code == keyword_tmps[0]:
                            item.score = 100
                        elif item.code.find(keyword_tmps[0]) != -1:
                            item.score = score
                            score += -5
                        else:
                            item.score = 20
                    if item.ui_code.find ('0000') != -1:
                        item.ui_code = item.ui_code.replace('0000', '-00').upper()
                    else:
                        item.ui_code = item.ui_code.replace('00', '-').upper()
                    if item.ui_code.endswith('-'):
                        item.ui_code = '%s00' % (item.ui_code[:-1])
                    logger.debug('score :%s %s ', item.score, item.ui_code)
                    ret['data'].append(item.as_dict())
                except Exception as exception: 
                    logger.error('Exception:%s', exception)
                    logger.error(traceback.format_exc()) 
            ret['data'] = sorted(ret['data'], key=lambda k: k['score'], reverse=True)  
            ret['ret'] = 'success'
            if len(ret['data']) == 0 and len(keyword_tmps) == 2 and len(keyword_tmps[1]) == 5:
                new_title = '%s%s' % (keyword_tmps[0], keyword_tmps[1].zfill(6))
                return cls.search(new_title, do_trans=do_trans, proxy_url=proxy_url, image_mode=image_mode)
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
            url = '%s/digital/videoa/-/detail/=/cid=%s/' % (cls.site_base_url, code[2:])
            tree = SiteUtil.get_tree(url, proxy_url=proxy_url, headers=cls.dmm_headers)
            
            entity = EntityMovie(cls.site_name, code)
            entity.country = [u'일본']
            entity.mpaa = u'청소년관람불가'
            entity.thumb = []
            basetag = '//*[@id="mu"]/div/table//tr/td[1]'
            nodes = tree.xpath('{basetag}/div[1]/div[2]'.format(basetag=basetag))
            if not nodes:
                logger.debug('CRITICAL!!!')
                return entity
            a_nodes = nodes[0].xpath('.//a[class="crs_full"]')
           
            # 2020-05-31 A태그가 없는 경우가 있음. 확대이미지가 없는 경우
            if a_nodes:
                nodes = a_nodes
                logger.debug(html.tostring(nodes[0]))
                img_tag = nodes[0].xpath('.//img')[0]
                data = SiteUtil.get_image_url(a_nodes[0].attrib['href'], image_mode, proxy_url=proxy_url, with_poster=True)
                entity.thumb.append(EntityThumb(aspect='landscape', value=data['image_url']))
                entity.thumb.append(EntityThumb(aspect='poster', value=data['poster_image_url']))
            else:
                img_tag = nodes[0].xpath('.//img')[0]
                entity.thumb.append(EntityThumb(aspect='poster', value=SiteUtil.process_image_mode(image_mode, img_tag.attrib['src'], proxy_url=proxy_url)))
  
            entity.tagline = SiteUtil.trans(img_tag.attrib['alt'], do_trans=do_trans)
            tags = tree.xpath('{basetag}/table//tr'.format(basetag=basetag))
            tmp_premiered = None
            for tag in tags:
                td_tag = tag.xpath('.//td')
                if len(td_tag) != 2:
                    continue
                key = td_tag[0].text_content().strip()
                value = td_tag[1].text_content().strip()
                if value == '----':
                    continue
                if key == u'商品発売日：':
                    entity.premiered = value.replace('/', '-')
                    entity.year = int(value[:4])
                elif key == u'配信開始日：':
                    tmp_premiered = value.replace('/', '-')
                elif key == u'収録時間：':
                    entity.runtime = int(value.replace(u'分', ''))
                elif key == u'出演者：':
                    entity.actor = []
                    a_tags = tag.xpath('.//a')
                    for a_tag in a_tags:
                        tmp = a_tag.text_content().strip()
                        if tmp == u'▼すべて表示する':
                            break
                        entity.actor.append(EntityActor(tmp))
                    #for v in value.split(' '):
                    #    entity.actor.append(EntityActor(v.strip()))
                elif key == u'監督：':
                    entity.director =  value                  
                elif key == u'シリーズ：':
                    if entity.tag is None:
                        entity.tag = []
                    entity.tag.append(SiteUtil.trans(value, do_trans=do_trans))
                elif key == u'レーベル：':
                    entity.studio = value
                    if do_trans:
                        if value in SiteUtil.av_studio:
                            entity.studio = SiteUtil.av_studio[value]
                        else:
                            entity.studio = SiteUtil.trans(value, do_trans=do_trans)
                elif key == u'ジャンル：':
                    a_tags = td_tag[1].xpath('.//a')
                    entity.genre = []
                    for tag in a_tags:
                        tmp = tag.text_content().strip()
                        if tmp.find('％OFF') != -1:
                            continue
                        if tmp in SiteUtil.av_genre:
                            entity.genre.append(SiteUtil.av_genre[tmp])
                        elif tmp in SiteUtil.av_genre_ignore_ja:
                            continue
                        else:
                            genre_tmp = SiteUtil.trans(tmp, do_trans=do_trans).replace(' ', '')
                            if genre_tmp not in SiteUtil.av_genre_ignore_ko:
                                entity.genre.append(genre_tmp)
                elif key == u'品番：':
                    match = re.compile(r'(h_)?\d*(?P<real>[a-zA-Z]+)(?P<no>\d+)([a-zA-Z]+)?$').match(value)
                    if match:
                        value = '%s-%s' % (match.group('real').upper(), str(int(match.group('no'))).zfill(3))
                        if entity.tag is None:
                            entity.tag = []
                        entity.tag.append(match.group('real').upper())
                    entity.title = entity.originaltitle = entity.sorttitle = value
            if entity.premiered is None and tmp_premiered is not None:
                entity.premiered = tmp_premiered
                entity.year = int(tmp_premiered[:4])

            try:
                tag = tree.xpath('{basetag}/table//tr[13]/td[2]/img'.format(basetag=basetag))
                if tag:
                    match = re.compile(r'(?P<rating>[\d|_]+)\.gif').search(tag[0].attrib['src'])
                    if match:
                        tmp = match.group('rating')
                        entity.ratings = [EntityRatings(float(tmp.replace('_', '.')), max=5, name='dmm', image_url=tag[0].attrib['src'])]
            except Exception as exception: 
                logger.error('Exception:%s', exception)
                logger.error(traceback.format_exc())

            tmp = tree.xpath('{basetag}/div[4]/text()'.format(basetag=basetag))[0]
            tmp = tmp.split('※')[0].strip()
            entity.plot = SiteUtil.trans(tmp, do_trans=do_trans)

            nodes = tree.xpath('//*[@id="sample-image-block"]/a')
            entity.fanart = []
            for idx, node in enumerate(nodes):
                if idx > 9:
                    break
                tag = node.xpath('.//img')
                tmp = tag[0].attrib['src']
                image_url = tag[0].attrib['src'].replace(entity.code[2:]+'-', entity.code[2:]+'jp-')
                entity.fanart.append(SiteUtil.process_image_mode(image_mode, image_url, proxy_url=proxy_url))
                
            try:
                if tree.xpath('//div[@class="d-review__points"]/p[1]/strong'):
                    point = float(tree.xpath('//div[@class="d-review__points"]/p[1]/strong')[0].text_content().replace(u'点', '').strip())
                    votes = int(tree.xpath('//div[@class="d-review__points"]/p[2]/strong')[0].text_content().strip())
                    entity.ratings[0].value = point
                    entity.ratings[0].votes = votes
            except Exception as exception: 
                logger.error('Exception:%s', exception)
                logger.error(traceback.format_exc())

            try:
                tmp = tree.xpath('//*[@id="detail-sample-movie"]/div/a')
                if tmp:
                    tmp = tmp[0].attrib['onclick']
                    url = cls.site_base_url + tmp.split("'")[1]
                    url = SiteUtil.get_tree(url, proxy_url=proxy_url, headers=cls.dmm_headers).xpath('//iframe')[0].attrib['src']
                    text = SiteUtil.get_text(url, proxy_url=proxy_url, headers=cls.dmm_headers)
                    pos = text.find('var params = {')
                    data = json.loads(text[text.find('{', pos):text.find(';', pos)])
                    #logger.debug(json.dumps(data, indent=4))
                    data['bitrates'] = sorted(data['bitrates'], key=lambda k: k['bitrate'], reverse=True)
                    entity.extras = [EntityExtra('trailer', SiteUtil.trans(data['title'], do_trans=do_trans), 'mp4', 'https:%s' % data['bitrates'][0]['src'])]
            except Exception as exception: 
                logger.error('Exception:%s', exception)
                logger.error(traceback.format_exc())
            ret['ret'] = 'success'
            ret['data'] = entity.as_dict()

        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
            ret['ret'] = 'exception'
            ret['data'] = str(exception)
        return ret

# -*- coding: utf-8 -*-
import requests, re, json
import traceback

from lxml import html

from framework import SystemModelSetting, py_urllib
from framework.util import Util
from system import SystemLogicTrans

from .plugin import P
from .entity_base import EntityMovie, EntityThumb, EntityActor, EntityRatings, EntityExtra, EntitySearchItemTv
from .site_util import SiteUtil

logger = P.logger


class SiteDaum(object):
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    @classmethod
    def get_show_info_on_home(cls, root):
        try:
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/a')
            # 2019-05-13
            #일밤- 미스터리 음악쇼 복면가왕 A 태그 2개
            if len(tags) < 1:
                return
            tag_index = len(tags)-1
            #entity = {}
            entity = EntitySearchItemTv('daum')

            entity.title = tags[tag_index].text
            match = re.compile(r'q\=(?P<title>.*?)&').search(tags[tag_index].attrib['href'])
            if match:
                entity.title = py_urllib.unquote(match.group('title'))
            entity.code = re.compile(r'irk\=(?P<id>\d+)').search(tags[tag_index].attrib['href']).group('id')

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/span')
            if len(tags) == 1:
                if tags[0].text == u'방송종료' or tags[0].text == u'완결':
                    entity.status = 2
                elif tags[0].text == u'방송예정':
                    entity.status = 0

            entity.image_url = root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')[0].attrib['src']


            logger.debug('get_show_info_on_home status: %s', entity.status)
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div')
            entity.extra_info = tags[0].text_content().strip()

            logger.debug('get_show_info_on_home extra_info: %s', entity.extra_info)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/a')
            if len(tags) == 1:
                entity.studio = tags[0].text
            else:
                tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span[1]')
                if len(tags) == 1:
                    entity.studio = tags[0].text
            logger.debug('get_show_info_on_home studio: %s', entity.studio)

            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span')
            extra_infos = [tag.text for tag in tags]
            entity.broadcast_info = extra_infos[-2].strip()
            entity.broadcast_term = extra_infos[-1].split(',')[-1].strip()
            entity.year = re.compile(r'(?P<year>\d{4})').search(extra_infos[-1]).group('year')
            
            #logger.debug('get_show_info_on_home 1: %s', entity['status'])
            #시리즈
            entity.series = []
            entity.series.append({'title':entity.title, 'id' : entity.code, 'year' : entity.year})
            tags = root.xpath('//*[@id="tv_series"]/div/ul/li')

            if tags:
                # 2019-03-05 시리즈 더보기 존재시
                try:
                    more = root.xpath('//*[@id="tv_series"]/div/div/a')
                    url = more[0].attrib['href']
                    if not url.startswith('http'):
                        url = 'https://search.daum.net/search%s' % url
                    logger.debug('MORE URL : %s', url)
                    if more[0].xpath('span')[0].text == u'시리즈 더보기':
                        #more_root = HTML.ElementFromURL(url)
                        more_root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
                        tags = more_root.xpath('//*[@id="series"]/ul/li')
                except Exception as exception:
                    logger.debug('Not More!')
                    logger.debug(traceback.format_exc())

                for tag in tags:
                    dic = {}
                    dic['title'] = tag.xpath('a')[0].text
                    dic['code'] = re.compile(r'irk\=(?P<id>\d+)').search(tag.xpath('a')[0].attrib['href']).group('id')
                    if tag.xpath('span'):
                        dic['date'] = tag.xpath('span')[0].text
                        dic['year'] = re.compile(r'(?P<year>\d{4})').search(dic['date']).group('year')
                    else:
                        dic['year'] = None
                    entity.series.append(dic)
                entity.series = sorted(entity.series, key=lambda k: int(k['id'])) 
            logger.debug('SERIES : %s', len(entity.series))
            #동명
            entity.equal_name = []
            tags = root.xpath(u'//div[@id="tv_program"]//dt[contains(text(),"동명 콘텐츠")]//following-sibling::dd')
            if tags:
                tags = tags[0].xpath('*')
                for tag in tags:
                    if tag.tag == 'a':
                        dic = {}
                        dic['title'] = tag.text
                        dic['code'] = re.compile(r'irk\=(?P<id>\d+)').search(tag.attrib['href']).group('id')
                    elif tag.tag == 'span':
                        match = re.compile(r'\((?P<studio>.*?),\s*(?P<year>\d{4})?\)').search(tag.text)
                        if match:
                            dic['studio'] = match.group('studio')
                            dic['year'] = match.group('year')
                        elif tag.text == u'(동명프로그램)':
                            entity['equal_name'].append(dic)
                        elif tag.text == u'(동명회차)':
                            continue
            logger.debug(entity)
            return entity.as_dict()
        except Exception as exception:
            logger.debug('Exception get_show_info_by_html : %s', exception)
            logger.debug(traceback.format_exc())



class SiteDaumTv(SiteDaum):
    site_name = 'daum'
    site_base_url = 'https://search.daum.net'
    module_char = 'K'
    site_char = 'D'

    

    @classmethod 
    def search(cls, keyword, daum_id=None, year=None, image_mode='0'):
        try:
            from system.logic_site import SystemLogicSite

            ret = {}
            if daum_id is None:
                url = 'https://search.daum.net/search?q=%s' % (py_urllib.quote(keyword.encode('utf8')))
            else:
                url = 'https://search.daum.net/search?q=%s&irk=%s&irt=tv-program&DA=TVP' % (py_urllib.quote(keyword.encode('utf8')), daum_id)

            root = SiteUtil.get_tree(url, headers=cls.default_headers, cookies=SystemLogicSite.get_daum_cookies())
            data = cls.get_show_info_on_home(root)
            logger.debug(data)

            return data

            return DaumTV.get_lxml_by_url(url)


            url = '%s/digital/videoa/-/list/search/=/?searchstr=%s' % (cls.site_base_url, dmm_keyword)
            tree = SiteUtil.get_tree(url, proxy_url=proxy_url, headers=cls.dmm_headers)

            logger.debug('2222222222222222222222')
            logger.debug(tree)
            lists = tree.xpath('//*[@id="list"]/li')
            ret = {'data' : []}
            score = 60
            logger.debug('len lists2 :%s', len(lists))
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
            nodes = tree.xpath('{basetag}/div[1]/div'.format(basetag=basetag))
            if not nodes:
                logger.debug('CRITICAL!!!')
                return entity
            a_nodes = nodes[0].xpath('.//a')
            
            # 2020-05-31 A태그가 없는 경우가 있음. 확대이미지가 없는 경우
            if a_nodes:
                nodes = a_nodes
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
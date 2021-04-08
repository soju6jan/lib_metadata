# -*- coding: utf-8 -*-
# python
import os, traceback, time, json

# third-party
import requests
from flask import Blueprint, request, send_file, redirect

# sjva 공용
from framework import app, path_data, check_api, py_urllib, SystemModelSetting
from framework.logger import get_logger
from framework.util import Util


from .plugin import P
logger = P.logger
# 패키지


server_plugin_ddns = 'https://meta.sjva.me'
server_web = 'https://sjva.me'
try:
    if SystemModelSetting.get('ddns') == server_plugin_ddns:
        server_plugin_ddns = 'http://127.0.0.1:19999'
except:
    pass

class MetadataServerUtil(object):
    @classmethod
    def get_metadata(cls, code):
        try:
            from framework import py_urllib
            #url = '{server_plugin_ddns}/server/normal/metadata/get?code={code}'.format(server_plugin_ddns=server_plugin_ddns, code=code)
            #url = '{server_web}/meta/get_meta.php?type=meta&code={code}'.format(server_web=server_web, code=code)
            #logger.debug(code)
            url = '{server_web}/meta/get_meta.php?'.format(server_web=server_web)
            url += py_urllib.urlencode({'type':'meta', 'code':code})
            #logger.debug(url)
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception:
            #logger.debug('Exception:%s', exception)
            #logger.debug(traceback.format_exc())
            logger.error('metaserver connection fail.. get_metadata')
    
    """
    @classmethod
    def search_metadata(cls, keyword):
        try:
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/metadata/search?keyword={keyword}'.format(server_plugin_ddns=server_plugin_ddns, keyword=keyword)
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('metaserver connection fail.. search_metadata')
    """

    @classmethod
    def set_metadata(cls, code, data, keyword):
        try:
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/metadata/set'.format(server_plugin_ddns=server_plugin_ddns)
            param = {'code':code, 'data':json.dumps(data), 'user':SystemModelSetting.get('sjva_me_user_id'), 'keyword':keyword}
            #logger.debug(param)
            data = requests.post(url, data=param).json()
            if data['ret'] == 'success':
                logger.info('%s Data save success. Thanks!!!!', code)
        except Exception as exception: 
            logger.error('metaserver connection fail.. set_metadata')


    @classmethod
    def set_metadata_jav_censored(cls, code, data, keyword):
        try:
            if data['thumb'] is None or (code.startswith('C') and len(data['thumb']) < 2) or (code.startswith('D') and len(data['thumb']) < 1):
                return
            for tmp in data['thumb']:
                if tmp['value'] is None or tmp['value'].find('.discordapp.') == -1:
                    return
                if requests.get(tmp['value']).status_code != 200:
                    return
            if SiteUtil.is_include_hangul(data['plot']) == False:
                return
            """
            if data['fanart'] is not None:
                for tmp in data['fanart']:
                    if tmp.find('.discordapp.') == -1:
                        return
            """
            cls.set_metadata(code, data, keyword)   
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    """
    @classmethod
    def get_actor_name_en(cls, name):
        try:
            tmp = 'https://sjva-dev.soju6jan.com'
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/actor/get?name={name}'.format(server_plugin_ddns=tmp, name=py_urllib.quote(name))
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('metaserver connection fail.. get_actor_name_en')
    

    @classmethod
    def trans_en_to_ko(cls, name):
        try:
            tmp = 'https://sjva-dev.soju6jan.com'
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/actor/trans_en_to_ko?name={name}'.format(server_plugin_ddns=tmp, name=py_urllib.quote(name))
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('metaserver connection fail.. get_actor_name_en')
    """
    
    @classmethod
    def get_meta_extra(cls, code):
        try:
            from framework import py_urllib
            #url = '{server_plugin_ddns}/server/normal/meta_extra/get?code={code}'.format(server_plugin_ddns=server_plugin_ddns, code=code)
            #url = '{server_web}/meta/get_meta.php?type=extra&code={code}'.format(server_web=server_web, code=py_urllib.quote(code))
            url = '{server_web}/meta/get_meta.php?'.format(server_web=server_web)
            url += py_urllib.urlencode({'type':'extra', 'code':code})
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('metaserver connection fail.. get_meta_extra')
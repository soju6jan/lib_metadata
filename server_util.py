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

server_plugin_ddns = 'https://sjva-server.soju6jan.com'

class MetadataServerUtil(object):
    @classmethod
    def get_metadata(cls, code):
        try:
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/metadata/get?code={code}'.format(server_plugin_ddns=server_plugin_ddns, code=code)
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    
    @classmethod
    def search_metadata(cls, keyword):
        try:
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/metadata/search?keyword={keyword}'.format(server_plugin_ddns=server_plugin_ddns, keyword=keyword)
            data = requests.get(url).json()
            if data['ret'] == 'success':
                return data['data']
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc()) 

    @classmethod
    def set_metadata(cls, code, data, keyword):
        try:
            from framework import py_urllib
            url = '{server_plugin_ddns}/server/normal/metadata/set'.format(server_plugin_ddns=server_plugin_ddns)
            param = {'code':code, 'data':json.dumps(data), 'user':SystemModelSetting.get('sjva_me_user_id'), 'keyword':keyword}
            data = requests.post(url, data=param).json()
            if data['ret'] == 'success':
                logger.info('%s Data save success. Thanks!!!!', code)
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

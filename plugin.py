# -*- coding: utf-8 -*-
# python
import os, traceback
# third-party
from flask import Blueprint
# sjva 공용
from framework.logger import get_logger
from framework import app, path_data
from framework.util import Util
from plugin import get_model_setting, Logic, default_route, PluginUtil
# 패키지
#########################################################
class P(object):
    package_name = __name__.split('.')[0]
    logger = get_logger(package_name)
    blueprint = menu = None

    plugin_info = {
        'version' : '0.2.0.0',
        'type' : 'library',
        'name' : package_name,
        'category_name' : 'library',
        'developer' : u'soju6jan',
        'description' : u'메타데이터를 얻기 위한 개별 사이트 크롤링 라이브러리',
        'home' : 'https://github.com/soju6jan/%s' % package_name,
        'more' : '',
    }
    ModelSetting = get_model_setting(package_name, logger)

    @staticmethod
    def plugin_load():
        P.logger.debug('%s plugin_load' % P.package_name)

    @staticmethod
    def plugin_unload():
        P.logger.debug('%s plugin_unload' % P.package_name)


def initialize():
    try:
        app.config['SQLALCHEMY_BINDS'][P.package_name] = 'sqlite:///%s' % (os.path.join(path_data, 'db', '{package_name}.db'.format(package_name=P.package_name)))
        PluginUtil.make_info_json(P.plugin_info, __file__)
    except Exception as e: 
        P.logger.error('Exception:%s', e)
        P.logger.error(traceback.format_exc())

initialize()

